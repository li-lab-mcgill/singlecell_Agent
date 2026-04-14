import importlib
import sys
import types
import unittest
from pathlib import Path


if "textgrad" not in sys.modules:
    fake_textgrad = types.ModuleType("textgrad")
    fake_textgrad.get_engine = lambda *args, **kwargs: None
    fake_textgrad.Variable = object
    sys.modules["textgrad"] = fake_textgrad

if "dotenv" not in sys.modules:
    fake_dotenv = types.ModuleType("dotenv")
    fake_dotenv.load_dotenv = lambda *args, **kwargs: None
    sys.modules["dotenv"] = fake_dotenv

if "consultant" not in sys.modules:
    fake_consultant = types.ModuleType("consultant")
    fake_consultant._short = lambda text, max_chars: str(text)[:max_chars]
    sys.modules["consultant"] = fake_consultant

if "config" not in sys.modules:
    fake_config = types.ModuleType("config")

    class _Config:
        pass

    fake_config.Config = _Config
    sys.modules["config"] = fake_config

if "multieval_types" not in sys.modules:
    fake_multieval_types = types.ModuleType("multieval_types")
    fake_multieval_types.STAGE_FILENAMES = [
        "prior_construction.py",
        "data_preprocess.py",
        "model_training.py",
        "downstream_analysis.py",
    ]
    sys.modules["multieval_types"] = fake_multieval_types


evaluator = importlib.import_module("evaluator")
evaluator_prompts = importlib.import_module("evaluator_prompts")


class EvaluatorMeetingTests(unittest.TestCase):
    def test_meeting_order_constant_is_biology_first(self):
        self.assertEqual(
            evaluator.EVALUATOR_MEETING_ORDER,
            ["biology", "data_science", "model", "prior"],
        )

    def test_synthesized_critic_payload_follows_meeting_order(self):
        payload = evaluator.synthesize_critic_payload_from_evaluators(
            step=3,
            evaluator_payloads={
                "prior": {"role": "prior", "feedback": "prior feedback"},
                "data_science": {"role": "data_science", "feedback": "data feedback"},
                "model": {"role": "model", "feedback": "model feedback"},
                "biology": {"role": "biology", "feedback": "biology feedback"},
            },
        )
        self.assertEqual(
            payload["global_rationale"],
            "[biology] biology feedback\n\n[data_science] data feedback\n\n[model] model feedback\n\n[prior] prior feedback",
        )
        self.assertEqual(
            list(payload["targets"].keys()),
            [
                "downstream_analysis.py",
                "data_preprocess.py",
                "model_training.py",
                "prior_construction.py",
            ],
        )

    def test_default_runtime_calls_evaluators_in_biology_first_order(self):
        source = Path("/Users/vickydong/Documents/singlecell_Agent/default.py").read_text(encoding="utf-8")
        biology_idx = source.index("biology_evaluator.loss_fn(")
        data_science_idx = source.index("data_science_evaluator.loss_fn(")
        model_idx = source.index("model_evaluator.loss_fn(")
        prior_idx = source.index("prior_evaluator.loss_fn(")
        self.assertLess(biology_idx, data_science_idx)
        self.assertLess(data_science_idx, model_idx)
        self.assertLess(model_idx, prior_idx)

    def test_prompt_framing_describes_biology_first_meeting(self):
        self.assertIn("You are the first evaluator in the meeting.", evaluator_prompts.BIOLOGY_EVALUATOR_SYSTEM_PROMPT)
        self.assertIn("You speak after the biology evaluator", evaluator_prompts.DATA_SCIENCE_EVALUATOR_SYSTEM_PROMPT)
        self.assertIn("You speak after the biology and data-science evaluators", evaluator_prompts.MODEL_EVALUATOR_SYSTEM_PROMPT)
        self.assertIn("You speak after the biology, data-science, and model evaluators", evaluator_prompts.PRIOR_EVALUATOR_SYSTEM_PROMPT)
        self.assertIn("The meeting order is biology first, then data science, model, and prior.", evaluator_prompts.CRITIC_SYSTEM_PROMPT)

    def test_escape_format_braces_handles_json_guidance(self):
        escaped = evaluator._escape_format_braces('{"task_category": "clustering", "components": [{"key": "combined_score"}]}')
        self.assertEqual(
            escaped,
            '{{"task_category": "clustering", "components": [{{"key": "combined_score"}}]}}',
        )


if __name__ == "__main__":
    unittest.main()
