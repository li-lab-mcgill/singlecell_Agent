import sys
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

try:
    import pandas as pd
except Exception:
    fake_pandas = types.ModuleType("pandas")

    class _FakeSeries(list):
        def astype(self, _dtype):
            return _FakeSeries(str(item) for item in self)

        def tolist(self):
            return list(self)

    class _FakeDataFrame:
        def __init__(self, data):
            self._data = data
            self.columns = list(data.keys())

        def __getitem__(self, key):
            return self._data[key]

    fake_pandas.Series = lambda data: _FakeSeries(list(data))
    fake_pandas.DataFrame = _FakeDataFrame
    fake_pandas.read_excel = lambda *args, **kwargs: _FakeDataFrame({})
    fake_pandas.read_csv = lambda *args, **kwargs: _FakeDataFrame({})
    sys.modules["pandas"] = fake_pandas
    import pandas as pd

if "dotenv" not in sys.modules:
    fake_dotenv = types.ModuleType("dotenv")
    fake_dotenv.load_dotenv = lambda *args, **kwargs: None
    sys.modules["dotenv"] = fake_dotenv

if "textgrad" not in sys.modules:
    fake_textgrad = types.ModuleType("textgrad")
    fake_textgrad.get_engine = lambda *args, **kwargs: None
    sys.modules["textgrad"] = fake_textgrad

if "numpy" not in sys.modules:
    sys.modules["numpy"] = types.ModuleType("numpy")

if "requests" not in sys.modules:
    fake_requests = types.ModuleType("requests")

    class _FakeSession:
        def get(self, *args, **kwargs):
            raise RuntimeError("network disabled in tests")

        def post(self, *args, **kwargs):
            raise RuntimeError("network disabled in tests")

    fake_requests.Session = _FakeSession
    sys.modules["requests"] = fake_requests

from agent_runner import ToolCallingAgentRunner
from consultant import (
    validate_candidate_comparison,
    validate_implementation_plan,
    validate_prior_decision_payload,
)
from paper_store import SharedPaperStore
from rag_agent import ConsultantRAGAgent
from rag_types import RAGDocument, RAGSection


class _FakeResponsesAPI:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self._responses:
            raise AssertionError("No more fake responses configured")
        return self._responses.pop(0)


class _FakeClient:
    def __init__(self, responses):
        self.responses = _FakeResponsesAPI(responses)


class _FakeResponse:
    def __init__(self, response_id, output=None, output_text=""):
        self.id = response_id
        self.output = output or []
        self.output_text = output_text


class _FakeRagStore:
    def search_runtime(self, collection_name, query_text, n_results=12):
        return [
            types.SimpleNamespace(
                doc_id="pmc:1",
                title="PBMC benchmark paper",
                score=0.91,
                snippet="benchmark snippet",
                url="https://example.org/paper",
                section_type="methods",
            )
        ]


class _FakeRagAgent:
    def __init__(self, tmpdir: Path):
        self.store = _FakeRagStore()
        self._tmpdir = tmpdir

    def _summaries_path(self, session_key: str, channel_name: str) -> Path:
        return self._tmpdir / f"{session_key}_{channel_name}_summaries.json"

    def fetch_paper_section(self, paper_id: str, section_type: str):
        return {
            "paper_id": paper_id,
            "section_type": section_type.lower(),
            "chunks": ["chunk-1", "chunk-2", "chunk-3"],
        }

    def _generate_paper_summary(self, *, document, session_key, channel_name):
        return {
            "objective": f"summary for {document.doc_id}",
            "key_methods": "methods",
            "main_findings": "findings",
            "limitations": "limitations",
        }


class _FakeConfig:
    def __init__(self):
        self.feat_stats = "PBMC dataset summary"
        self.label_column = "cell_type"
        self.task_type = "Clustering"
        self.learning_type = "Unsupervised"
        self.prior_resource_summary = json.dumps({"prior_resources": [{"file_path": "/tmp/gene_embedding", "exists": True}]})
        self.dataset_dir = "/tmp"
        self.data_mod1_path = "/tmp/pbmc.h5ad"

    def _load_any(self, path):
        class _ObsFrame:
            def __init__(self, data):
                self._data = data
                self.columns = list(data.keys())

            def __getitem__(self, key):
                return self._data[key]

        adata = types.SimpleNamespace(
            obs=_ObsFrame({"cell_type": ["T", "T", "B"], "batch": ["b1", "b2", "b1"]}),
            var_names=["CD3D", "MS4A1", "LYZ"],
        )
        return {"type": "h5ad", "obj": adata}


class AgentLayerTests(unittest.TestCase):
    def test_runner_executes_tool_and_persists_trace(self):
        tool_call = {"type": "function_call", "call_id": "call_1", "name": "ping", "arguments": "{}"}
        final_message = {"type": "message", "content": [{"type": "output_text", "text": "{\"done\": true}"}]}
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = ToolCallingAgentRunner(
                model="gpt-test",
                system_prompt="system",
                tool_specs=[],
                tool_executor={"ping": lambda: {"pong": True}},
                transcript_path=str(Path(tmpdir) / "transcript.jsonl"),
                tool_trace_path=str(Path(tmpdir) / "tool_trace.jsonl"),
                client=_FakeClient([
                    _FakeResponse("r1", output=[tool_call]),
                    _FakeResponse("r2", output=[final_message], output_text='{"done": true}'),
                ]),
            )
            result = runner.run(
                initial_user_input="hello",
                response_handler=lambda text: {"done": True, "result": json.loads(text)},
            )
            self.assertEqual(result, {"done": True})
            transcript = (Path(tmpdir) / "transcript.jsonl").read_text(encoding="utf-8")
            tool_trace = (Path(tmpdir) / "tool_trace.jsonl").read_text(encoding="utf-8")
            self.assertIn('"role": "tool"', transcript)
            self.assertIn('"tool_name": "ping"', tool_trace)

    def test_shared_paper_store_reads_summary_distribution_and_sections(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rag_agent = _FakeRagAgent(Path(tmpdir))
            summary_path = rag_agent._summaries_path("sess", "benchmark")
            summary_path.write_text(
                json.dumps(
                    {
                        "pmc:1": {
                            "objective": "obj",
                            "key_methods": "methods",
                            "main_findings": "findings",
                            "limitations": "limits",
                        }
                    }
                ),
                encoding="utf-8",
            )
            prepared_contexts = {
                "benchmark": {
                    "documents": [
                        RAGDocument(
                            doc_id="pmc:1",
                            source="pmc",
                            source_id="1",
                            title="Paper",
                            text="",
                            sections=[RAGSection(section_id="methods:0", section_type="methods", heading="Methods", text="abc")],
                        )
                    ],
                    "session_key": "sess",
                    "collection_name": "runtime_benchmark",
                }
            }
            store = SharedPaperStore(rag_agent=rag_agent, config=_FakeConfig(), prepared_contexts=prepared_contexts)
            distribution = store.read_label_distribution("cell_type")
            self.assertEqual(distribution["distribution"][0]["label"], "T")
            summary = store.read_paper_summary("pmc:1")
            self.assertEqual(summary["summary"]["objective"], "obj")
            section = store.fetch_paper_section("pmc:1", "methods", top_n_chunks=2)
            self.assertEqual(len(section["chunks"]), 2)
            hits = store.search_index("PBMC benchmark", "benchmark", top_k=1)
            self.assertEqual(hits["results"][0]["paper_id"], "pmc:1")

    def test_consultant_validators_accept_expected_payloads(self):
        comparison = validate_candidate_comparison(
            {
                "candidate_approaches": [
                    {"label": "A", "summary": "a", "pros": ["p"], "cons": ["c"]},
                    {"label": "B", "summary": "b", "pros": [], "cons": []},
                    {"label": "C", "summary": "c", "pros": [], "cons": []},
                ],
                "selected_label": "B",
                "selection_reason": "best fit",
            }
        )
        self.assertEqual(comparison["selected_label"], "B")
        prior = validate_prior_decision_payload(
            {
                "use_priors": True,
                "decision_reason": "coverage is high",
                "selected_resource_names": ["MsigDB"],
                "prior_schema": {
                    "output_files": [
                        {"file_name": "prior_mask.csv", "description": "mask", "dtype": "csv", "shape": ["n_sets", "n_genes"]}
                    ]
                },
            }
        )
        self.assertTrue(prior["use_priors"])
        plan = validate_implementation_plan(
            {
                "task_summary": "PBMC clustering",
                "chosen_approach": "prior guided VAE",
                "prior_decision_summary": "use priors",
                "stage_plan": {
                    "prior_construction.py": "build pathway masks",
                    "data_preprocess.py": "normalize and split",
                    "model_training.py": "train model",
                    "downstream_analysis.py": "cluster and score",
                },
                "artifact_expectations": {"embedding": "n_cells x latent_dim"},
                "open_risks": ["batch effect"],
            }
        )
        self.assertEqual(plan["stage_plan"]["model_training.py"], "train model")

    def test_prepare_contexts_prior_methods_collection_matches_built_index(self):
        agent = ConsultantRAGAgent.__new__(ConsultantRAGAgent)
        agent.store = types.SimpleNamespace(
            runtime_collection_name=lambda session_key, channel_name: f"runtime_{session_key}_{channel_name}"
        )
        agent._prepared_channel_contexts = {}

        config = types.SimpleNamespace(
            feat_stats="PBMC dataset summary",
            prior_resource_summary="{}",
            task_type="Clustering",
            learning_type="Unsupervised",
            metrics="ari,nmi",
        )
        background = "TASK: PBMC clustering"

        with mock.patch.object(ConsultantRAGAgent, "_dataset_channel", return_value=[]), \
            mock.patch.object(ConsultantRAGAgent, "_prior_resource_channel", return_value=[]), \
            mock.patch.object(ConsultantRAGAgent, "_prior_method_channel", return_value=[]), \
            mock.patch.object(ConsultantRAGAgent, "_benchmark_channel", return_value=[]), \
            mock.patch.object(ConsultantRAGAgent, "_resolve_base_query", return_value="base query"), \
            mock.patch.object(ConsultantRAGAgent, "_format_summary_context", return_value=""), \
            mock.patch.object(ConsultantRAGAgent, "_document_hits", return_value=[]), \
            mock.patch.object(ConsultantRAGAgent, "_prior_resource_names", return_value=["MsigDB"]), \
            mock.patch.object(ConsultantRAGAgent, "_prior_resource_types", return_value=["pathway_gene_sets", "grn"]):
            prepared = ConsultantRAGAgent.prepare_contexts(agent, config, background)

        expected_session_key = ConsultantRAGAgent._channel_hash(
            agent,
            "prior_methods",
            {
                "prior_resource_summary": str(config.prior_resource_summary or ""),
                "feat_stats": str(config.feat_stats or ""),
                "task_type": str(config.task_type or ""),
                "learning_type": str(config.learning_type or ""),
                "metrics": str(config.metrics or ""),
                "prior_resource_types": ["pathway_gene_sets", "grn"],
            },
            "base query",
            background,
        )
        self.assertEqual(
            prepared["prior_methods"]["collection_name"],
            f"runtime_{expected_session_key}_prior_methods",
        )


if __name__ == "__main__":
    unittest.main()
