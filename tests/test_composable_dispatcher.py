import sys
import tempfile
import types
import unittest
from pathlib import Path


if "dotenv" not in sys.modules:
    fake_dotenv = types.ModuleType("dotenv")
    fake_dotenv.load_dotenv = lambda *args, **kwargs: None
    sys.modules["dotenv"] = fake_dotenv

if "pandas" not in sys.modules:
    fake_pandas = types.ModuleType("pandas")
    fake_pandas.DataFrame = type("DataFrame", (), {})
    fake_pandas.Series = lambda data: list(data)
    fake_pandas.read_excel = lambda *args, **kwargs: None
    fake_pandas.read_csv = lambda *args, **kwargs: None
    sys.modules["pandas"] = fake_pandas


from agents.session_dispatcher import SessionDispatcher
from agents.session_state import SessionStateStore


class _FakeToolConsultant:
    def __init__(self, decision):
        self.decision = decision

    def decide(self, **kwargs):
        return self.decision


class _FakeDagExecutor:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def execute(self, *, dag_plan, session_tag):
        self.calls.append({"dag_plan": dag_plan, "session_tag": session_tag})
        return self.result


class _FakeCoder:
    def __init__(self):
        self.calls = []

    def run(self, *, implementation_plan, session_state, session_tag):
        self.calls.append(
            {
                "implementation_plan": implementation_plan,
                "session_state": session_state,
                "session_tag": session_tag,
            }
        )
        return {"status": "completed", "message": "coder ok"}


class _FakeSummarizer:
    def __init__(self):
        self.calls = []

    def summarize(self, *, user_query, decision, raw_results, session_tag="result_summarizer"):
        self.calls.append(
            {
                "user_query": user_query,
                "decision": decision,
                "raw_results": raw_results,
                "session_tag": session_tag,
            }
        )
        return {"message": "summary", "figures": []}


class ComposableDispatcherTests(unittest.TestCase):
    def _dispatcher(self, tmpdir, *, decision, dag_result, research_executor=None):
        coder = _FakeCoder()
        summarizer = _FakeSummarizer()
        dispatcher = SessionDispatcher(
            router=None,
            tool_consultant=_FakeToolConsultant(decision),
            coder=coder,
            research_executor=research_executor,
            tool_artifact_dir=Path(tmpdir) / "artifacts",
            state_store=SessionStateStore(Path(tmpdir) / "session_state.json"),
            result_dir=tmpdir,
            dag_executor=_FakeDagExecutor(dag_result),
            result_summarizer=summarizer,
        )
        return dispatcher, coder, summarizer

    def test_dag_result_inputs_are_resolved_before_coder_runs(self):
        decision = {
            "task": "cluster and plot",
            "dag_plan": {"input_h5ad_path": "/tmp/input.h5ad", "layers": [{"stage": "qc", "variants": [{"method": "basic"}]}]},
            "implementation_plan": {
                "goal": "plot",
                "depends_on_dag": True,
                "inputs": {
                    "path_dir": "dag_output.path_dir",
                    "h5ad_path": "dag_output.resolved_outputs.output_h5ad_path",
                    "cluster_key": "dag_output.resolved_outputs.cluster_key",
                },
            },
            "research_brief": None,
        }
        dag_result = {
            "status": "completed",
            "best_path": {
                "path_dir": "/tmp/path_001",
                "artifacts": {"00_qc/output.h5ad": "/tmp/path_001/00_qc/output.h5ad"},
                "resolved_outputs": {
                    "output_h5ad_path": "/tmp/path_001/output.h5ad",
                    "cluster_key": "pca_clusters",
                },
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            dispatcher, coder, summarizer = self._dispatcher(tmpdir, decision=decision, dag_result=dag_result)
            payload = dispatcher.execute_task(user_message="cluster and plot", session_state={}, session_tag="turn1")

        self.assertEqual(payload["result"]["status"], "completed")
        self.assertEqual(len(coder.calls), 1)
        inputs = coder.calls[0]["implementation_plan"]["inputs"]
        self.assertEqual(inputs["path_dir"], "/tmp/path_001")
        self.assertEqual(inputs["h5ad_path"], "/tmp/path_001/output.h5ad")
        self.assertEqual(inputs["cluster_key"], "pca_clusters")
        self.assertEqual(coder.calls[0]["session_state"]["cluster_key"], "pca_clusters")
        self.assertEqual(summarizer.calls[0]["session_tag"], "turn1_result_summarizer")

    def test_dag_failure_skips_dag_dependent_coder(self):
        decision = {
            "task": "cluster and plot",
            "dag_plan": {"input_h5ad_path": "/tmp/input.h5ad", "layers": [{"stage": "qc", "variants": [{"method": "basic"}]}]},
            "implementation_plan": {
                "goal": "plot",
                "depends_on_dag": True,
                "inputs": {"path_dir": "dag_output.path_dir"},
            },
            "research_brief": None,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            dispatcher, coder, _summarizer = self._dispatcher(
                tmpdir,
                decision=decision,
                dag_result={"status": "failed", "error": "all paths failed"},
            )
            payload = dispatcher.execute_task(user_message="cluster and plot", session_state={}, session_tag="turn1")

        self.assertEqual(payload["result"]["status"], "failed")
        self.assertEqual(coder.calls, [])

    def test_composable_research_runs_by_default(self):
        class _ResearchExecutor:
            def __init__(self):
                self.calls = []

            def execute(self, *, user_message, session_state, session_tag):
                self.calls.append(
                    {
                        "user_message": user_message,
                        "session_state": session_state,
                        "session_tag": session_tag,
                    }
                )
                return {"status": "completed", "message": "research ok"}

        decision = {
            "task": "research",
            "dag_plan": None,
            "implementation_plan": None,
            "research_brief": {"goal": "compare methods"},
        }
        research = _ResearchExecutor()

        with tempfile.TemporaryDirectory() as tmpdir:
            dispatcher, coder, _summarizer = self._dispatcher(
                tmpdir,
                decision=decision,
                dag_result={},
                research_executor=research,
            )
            payload = dispatcher.execute_task(user_message="research", session_state={}, session_tag="turn_research")

        self.assertEqual(payload["result"]["status"], "completed")
        self.assertEqual(coder.calls, [])
        self.assertEqual(len(research.calls), 1)


if __name__ == "__main__":
    unittest.main()
