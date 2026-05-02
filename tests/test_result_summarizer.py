import sys
import tempfile
import types
import unittest
from pathlib import Path


if "dotenv" not in sys.modules:
    fake_dotenv = types.ModuleType("dotenv")
    fake_dotenv.load_dotenv = lambda *args, **kwargs: None
    sys.modules["dotenv"] = fake_dotenv


from agents.result_summarizer import ResultSummarizer, _collect_figures


class _FakeResponses:
    def __init__(self, text):
        self.text = text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return types.SimpleNamespace(id="response_1", output=[], output_text=self.text)


class _FakeClient:
    def __init__(self, text):
        self.responses = _FakeResponses(text)


class ResultSummarizerTests(unittest.TestCase):
    def test_collect_figures_walks_nested_results_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            figure = Path(tmpdir) / "plot.png"
            figure.write_bytes(b"\x89PNG\r\n\x1a\n")
            raw = {
                "dag_result": {"artifacts": {"plot": str(figure)}},
                "coder_result": {"artifacts": {"same_plot": str(figure)}},
            }

            self.assertEqual(_collect_figures(raw), [str(figure)])

    def test_summarize_returns_message_and_figures(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            figure = Path(tmpdir) / "plot.svg"
            figure.write_text("<svg></svg>", encoding="utf-8")
            client = _FakeClient("Best path used leiden and produced plot.svg.")
            summarizer = ResultSummarizer(engine_name="fake", result_dir=tmpdir, client=client)

            result = summarizer.summarize(
                user_query="cluster and plot",
                decision={"task": "cluster"},
                raw_results={"coder_result": {"artifacts": {"plot": str(figure)}}},
                session_tag="turn1",
            )

        self.assertIn("Best path", result["message"])
        self.assertEqual(result["figures"], [str(figure)])

    def test_dag_only_summary_prompt_includes_best_path_and_comparison_table(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            client = _FakeClient("Best path 1 used scvi with ari 0.9.")
            summarizer = ResultSummarizer(engine_name="fake", result_dir=tmpdir, client=client)

            result = summarizer.summarize(
                user_query="compare clustering methods",
                decision={"task": "cluster", "dag_plan": {"layers": [{"stage": "rna_clustering"}]}},
                raw_results={
                    "dag_result": {
                        "status": "completed",
                        "best_path": {
                            "path_index": 1,
                            "config": [{"stage": "rna_clustering", "method": "scvi"}],
                            "metrics": {"ari": 0.9},
                        },
                        "comparison_table": [
                            {"path_index": 0, "rna_clustering_method": "pca", "ari": 0.7},
                            {"path_index": 1, "rna_clustering_method": "scvi", "ari": 0.9},
                        ],
                    }
                },
                session_tag="dag_only",
            )

        prompt = client.responses.calls[0]["input"][1]["content"]
        self.assertIn("best_path", prompt)
        self.assertIn("comparison_table", prompt)
        self.assertIn("scvi", prompt)
        self.assertIn("Best path 1", result["message"])

    def test_dag_plus_coder_summary_prompt_includes_metrics_and_coder_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            figure = Path(tmpdir) / "markers.png"
            figure.write_bytes(b"\x89PNG\r\n\x1a\n")
            client = _FakeClient("DAG selected leiden and coder produced markers.png.")
            summarizer = ResultSummarizer(engine_name="fake", result_dir=tmpdir, client=client)

            result = summarizer.summarize(
                user_query="cluster and plot markers",
                decision={"task": "cluster and plot", "dag_plan": {}, "implementation_plan": {}},
                raw_results={
                    "dag_result": {
                        "status": "completed",
                        "best_path": {"metrics": {"ari": 0.88}, "path_dir": "/tmp/path_001"},
                    },
                    "coder_result": {
                        "status": "completed",
                        "metrics": {"marker_count": 30},
                        "artifacts": {"marker_plot": str(figure)},
                    },
                },
                session_tag="dag_plus_coder",
            )

        prompt = client.responses.calls[0]["input"][1]["content"]
        self.assertIn("ari", prompt)
        self.assertIn("marker_count", prompt)
        self.assertIn("markers.png", prompt)
        self.assertEqual(result["figures"], [str(figure)])


if __name__ == "__main__":
    unittest.main()
