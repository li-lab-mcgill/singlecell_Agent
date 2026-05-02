import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


if "textgrad" not in sys.modules:
    fake_textgrad = types.ModuleType("textgrad")
    fake_textgrad.get_engine = lambda *args, **kwargs: None
    sys.modules["textgrad"] = fake_textgrad

if "pandas" not in sys.modules:
    fake_pandas = types.ModuleType("pandas")
    class _FakeSeries(list):
        def astype(self, _dtype):
            return _FakeSeries(str(item) for item in self)

        def tolist(self):
            return list(self)

    fake_pandas.DataFrame = type("DataFrame", (), {})
    fake_pandas.Series = lambda data: _FakeSeries(list(data))
    fake_pandas.read_excel = lambda *args, **kwargs: None
    fake_pandas.read_csv = lambda *args, **kwargs: None
    sys.modules["pandas"] = fake_pandas

if "numpy" not in sys.modules:
    sys.modules["numpy"] = types.ModuleType("numpy")

if "dotenv" not in sys.modules:
    fake_dotenv = types.ModuleType("dotenv")
    fake_dotenv.load_dotenv = lambda *args, **kwargs: None
    sys.modules["dotenv"] = fake_dotenv


from agents.coder import CoderAgent
from agents.decision_schema import DecisionValidationError, validate_implementation_plan


class _FakeEngine:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        if not self.responses:
            raise AssertionError("No fake engine responses left")
        return self.responses.pop(0)


class _FakeVariable:
    def __init__(self, value, **kwargs):
        self.value = value

    def set_value(self, value):
        self.value = value


class _FakeOptimizer:
    def __init__(self, **kwargs):
        pass

    def zero_grad(self):
        pass

    def step(self):
        pass


class _FakeLoss:
    value = '{"passed": false, "feedback": "improve the output"}'

    def backward(self):
        pass


class _ValueLoss:
    def __init__(self, value):
        self.value = value

    def backward(self):
        pass


class _FakeEvaluator:
    def loss_fn(self, **kwargs):
        return _FakeLoss()


class _SequencedEvaluator:
    def __init__(self, values):
        self.values = list(values)

    def loss_fn(self, **kwargs):
        if not self.values:
            raise AssertionError("No fake evaluator responses left")
        return _ValueLoss(self.values.pop(0))


class _BugIntroducingOptimizer:
    broken_script = "print('optimized but broken'"

    def __init__(self, **kwargs):
        self.parameters = kwargs["parameters"]

    def zero_grad(self):
        pass

    def step(self):
        self.parameters[0].set_value(self.broken_script)


class CoderAgentTests(unittest.TestCase):
    def test_validate_implementation_plan_accepts_dag_references(self):
        plan = validate_implementation_plan(
            {
                "goal": "Plot marker heatmap",
                "depends_on_dag": True,
                "inputs": {
                    "path_dir": "dag_output.path_dir",
                    "cluster_key": "dag_output.resolved_outputs.cluster_key",
                },
            }
        )

        self.assertTrue(plan["depends_on_dag"])
        self.assertEqual(plan["dag_input_source"], "best_path")
        self.assertEqual(plan["inputs"]["cluster_key"], "dag_output.resolved_outputs.cluster_key")

    def test_validate_implementation_plan_rejects_placeholders(self):
        with self.assertRaises(DecisionValidationError):
            validate_implementation_plan(
                {
                    "goal": "Use labels",
                    "inputs": {"label_key": "<ground_truth_label_key>"},
                }
            )

    def test_coder_fix_loop_repairs_script_and_records_plan_trace(self):
        broken_script = "print('unterminated"
        fixed_script = """
import json
from pathlib import Path

Path('result.txt').write_text('ok', encoding='utf-8')
Path('metrics.json').write_text(json.dumps({'metrics': {'ari': 1.0, 'nmi': 1.0, 'silhouette': 1.0}}), encoding='utf-8')
"""
        engine = _FakeEngine(
            [
                f"```python\n{broken_script}\n```",
                f"```python\n{fixed_script}\n```",
            ]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            agent = CoderAgent(
                engine_name="fake",
                result_dir=tmpdir,
                max_fix_step=2,
                max_opt_step=0,
            )
            agent.engine = engine

            report = agent.run(
                implementation_plan={
                    "script_name": "solution.py",
                    "goal": "Write a result file and metrics",
                    "inputs": {"h5ad_path": "/tmp/input.h5ad"},
                    "outputs": {"result": "result.txt", "metrics": "metrics.json"},
                    "success_metric": "cell_type_annotation_default",
                },
                session_state={},
                session_tag="turn1",
            )

        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["attempts"], 2)
        self.assertEqual(report["plan_trace"]["revisions"], [])
        self.assertIn("cell_type_annotation_default", report["metrics"])
        self.assertEqual(report["attempt_log"][0]["phase"], "fix")
        self.assertEqual(report["attempt_log"][0]["execution_result"]["returncode"], 1)
        self.assertEqual(report["attempt_log"][1]["execution_result"]["returncode"], 0)

    def test_coder_optimization_returns_partial_when_evaluator_never_passes(self):
        valid_script = "print('ok')\n"
        engine = _FakeEngine([f"```python\n{valid_script}\n```"])

        with tempfile.TemporaryDirectory() as tmpdir:
            agent = CoderAgent(
                engine_name="fake",
                result_dir=tmpdir,
                max_fix_step=0,
                max_opt_step=1,
            )
            agent.engine = engine
            with mock.patch("agents.coder._textgrad_optimization_available", return_value=True), \
                mock.patch("agents.coder.CoderEvaluator", return_value=_FakeEvaluator()), \
                mock.patch("agents.coder.tg.Variable", _FakeVariable, create=True), \
                mock.patch("agents.coder.tg.TextualGradientDescent", _FakeOptimizer, create=True):
                report = agent.run(
                    implementation_plan={
                        "script_name": "solution.py",
                        "goal": "Run but fail evaluator",
                        "inputs": {"h5ad_path": "/tmp/input.h5ad"},
                    },
                    session_state={},
                    session_tag="turn_partial",
                )

        self.assertEqual(report["status"], "partial")
        self.assertIn("evaluator did not confirm", report["remaining_gaps"][0])

    def test_coder_inner_fix_loop_recovers_from_broken_optimization_step(self):
        initial_script = """
from pathlib import Path
Path('result.txt').write_text('initial', encoding='utf-8')
"""
        fixed_script = """
import json
from pathlib import Path
Path('result.txt').write_text('fixed', encoding='utf-8')
Path('metrics.json').write_text(json.dumps({'metrics': {'ari': 1.0, 'nmi': 1.0, 'silhouette': 1.0}}), encoding='utf-8')
"""
        engine = _FakeEngine(
            [
                f"```python\n{initial_script}\n```",
                f"```python\n{fixed_script}\n```",
            ]
        )
        evaluator = _SequencedEvaluator(
            [
                '{"passed": false, "feedback": "add metrics"}',
                '{"passed": true, "feedback": "looks good"}',
            ]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            agent = CoderAgent(
                engine_name="fake",
                result_dir=tmpdir,
                max_fix_step=1,
                max_opt_step=2,
            )
            agent.engine = engine
            with mock.patch("agents.coder._textgrad_optimization_available", return_value=True), \
                mock.patch("agents.coder.CoderEvaluator", return_value=evaluator), \
                mock.patch("agents.coder.tg.Variable", _FakeVariable, create=True), \
                mock.patch("agents.coder.tg.TextualGradientDescent", _BugIntroducingOptimizer, create=True):
                report = agent.run(
                    implementation_plan={
                        "script_name": "solution.py",
                        "goal": "Recover from a bad optimization edit",
                        "inputs": {"h5ad_path": "/tmp/input.h5ad"},
                        "outputs": {"result": "result.txt", "metrics": "metrics.json"},
                        "success_metric": "cell_type_annotation_default",
                    },
                    session_state={},
                    session_tag="turn_inner_fix",
                )

        self.assertEqual(report["status"], "completed")
        phases = [attempt["phase"] for attempt in report["attempt_log"]]
        self.assertIn("post_opt_fix", phases)
        post_opt_attempts = [attempt for attempt in report["attempt_log"] if attempt["phase"] == "post_opt_fix"]
        self.assertEqual(post_opt_attempts[0]["execution_result"]["returncode"], 1)
        self.assertEqual(post_opt_attempts[1]["execution_result"]["returncode"], 0)
        self.assertIn("cell_type_annotation_default", report["metrics"])

    def test_coder_fix_exhaustion_fails_before_optimization(self):
        broken_script = "print('still broken'"
        engine = _FakeEngine([f"```python\n{broken_script}\n```"])

        with tempfile.TemporaryDirectory() as tmpdir:
            agent = CoderAgent(
                engine_name="fake",
                result_dir=tmpdir,
                max_fix_step=0,
                max_opt_step=2,
            )
            agent.engine = engine
            with mock.patch("agents.coder._textgrad_optimization_available", side_effect=AssertionError("optimization should not run")):
                report = agent.run(
                    implementation_plan={
                        "script_name": "solution.py",
                        "goal": "Fail fast",
                        "inputs": {"h5ad_path": "/tmp/input.h5ad"},
                    },
                    session_state={},
                    session_tag="turn_fail_fast",
                )

        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["attempts"], 1)
        self.assertEqual(report["attempt_log"][0]["phase"], "fix")
        self.assertNotIn("optimize", [attempt["phase"] for attempt in report["attempt_log"]])


if __name__ == "__main__":
    unittest.main()
