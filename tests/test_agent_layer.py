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

    class _FakeResponse:
        def __init__(self):
            self.status_code = 200

    class _FakeHTTPError(Exception):
        def __init__(self, message="", response=None):
            super().__init__(message)
            self.response = response

    class _FakeSession:
        def get(self, *args, **kwargs):
            raise RuntimeError("network disabled in tests")

        def post(self, *args, **kwargs):
            raise RuntimeError("network disabled in tests")

    fake_requests.Response = _FakeResponse
    fake_requests.HTTPError = _FakeHTTPError
    fake_requests.ConnectionError = type("ConnectionError", (Exception,), {})
    fake_requests.Timeout = type("Timeout", (Exception,), {})
    fake_requests.Session = _FakeSession
    sys.modules["requests"] = fake_requests

if "scanpy" not in sys.modules:
    fake_scanpy = types.ModuleType("scanpy")
    fake_scanpy.read_h5ad = lambda *args, **kwargs: _FakeAnnData()
    sys.modules["scanpy"] = fake_scanpy

from agents.runner import ToolCallingAgentRunner
from agents.tools import (
    AtacComputeToolkit,
    MultimodalComputeToolkit,
    PaperToolkit,
    RnaComputeToolkit,
    build_analyst_registry,
    build_consultant_registry,
    build_tool_consultant_registry,
    build_tool_executor_registry,
    build_tool_registry,
)
from agents.consultant_agent import ConsultantAgent
from agents.consultant import (
    validate_candidate_comparison,
    validate_implementation_plan,
    validate_prior_decision_payload,
)
from rag.paper_store import PaperBackend
from rag.agent import ConsultantRAGAgent
from rag.types import RAGDocument, RAGSection
from backend.rna import _differential_expression as rna_differential_expression
from backend.rna import _batch_integration as rna_batch_integration
from backend.rna import _celltype_annotation as rna_celltype_annotation
from backend.rna import _dimensionality_reduction as rna_dimensionality_reduction
from backend.rna import _feature_selection as rna_feature_selection
from backend.rna import _normalization as rna_normalization
from backend.objectives import score_metrics
from backend.context_access import read_dataset_summary
from backend.types import DEResult, PeakCallResult
from backend.types import LinkSet
from agents.tool_consultant import ToolConsultantAgent


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


class _FakeAnnData:
    def __init__(self):
        self.n_obs = 3
        self.n_vars = 2
        self.obsm = {"X_pca": [[0.0, 0.1], [0.2, 0.3], [0.4, 0.5]]}
        self.obs = {"pca_clusters": ["0", "1", "0"]}
        self.var = {"highly_variable": [True, True]}
        self.uns = {"pca_clusters_metrics": {"ari": 1.0}}

    def write_h5ad(self, path):
        Path(path).write_text("fake", encoding="utf-8")


class _MiniObs(dict):
    @property
    def columns(self):
        return list(self.keys())


class _FakeRnaBackend:
    def __init__(self):
        self.last_integrate_kwargs = None

    def cluster(self, adata, **kwargs):
        cluster_key = kwargs.get("cluster_key") or f"{kwargs['embedding_key'].replace('X_', '')}_clusters"
        adata.obs[cluster_key] = ["0", "1", "0"]
        adata.uns[f"{cluster_key}_metrics"] = {"ari": 1.0, "nmi": 1.0}
        return adata

    def qc(self, adata, **kwargs):
        adata.uns["qc"] = {"method": kwargs.get("method", "basic")}
        return adata

    def normalize(self, adata, **kwargs):
        adata.uns["normalization"] = {"method": kwargs.get("method", "log1p")}
        return adata

    def select_features(self, adata, **kwargs):
        adata.var["highly_variable"] = [True, True]
        adata.uns["feature_selection"] = {"method": kwargs.get("method", "seurat_v3")}
        return adata

    def embed(self, adata, **kwargs):
        key = {
            "pca": "X_pca",
            "scvi": "X_scvi",
            "seurat_pca": "X_seurat_pca",
            "scanvi": "X_scanvi",
        }.get(kwargs.get("method"), "X_pca")
        adata.obsm[key] = [[0.0, 0.1], [0.2, 0.3], [0.4, 0.5]]
        return adata

    def integrate(self, adata, **kwargs):
        self.last_integrate_kwargs = kwargs
        method = kwargs.get("method")
        embedding_key = kwargs.get("embedding_key", "X_pca")
        if method == "harmony":
            output_key = "X_harmony" if embedding_key == "X_pca" else f"{embedding_key}_harmony"
            adata.obsm[output_key] = [[0.0, 0.1], [0.2, 0.3], [0.4, 0.5]]
        elif method == "scvi":
            adata.obsm["X_scvi_integrated"] = [[0.0, 0.1], [0.2, 0.3], [0.4, 0.5]]
        elif method == "scanorama":
            output_key = "X_scanorama" if embedding_key == "X_pca" else f"{embedding_key}_scanorama"
            adata.obsm[output_key] = [[0.0, 0.1], [0.2, 0.3], [0.4, 0.5]]
        elif method == "bbknn":
            adata.uns["neighbors"] = {"params": {}}
        adata.uns["batch_integration"] = {"method": method}
        return adata

    def annotate(self, adata, **kwargs):
        obs_cluster = kwargs.get("obs_cluster")
        annotation_key = f"{obs_cluster}_celltype" if obs_cluster else "celltype"
        adata.obs[annotation_key] = ["T cell", "B cell", "T cell"]
        adata.uns["annotation"] = {"method": kwargs.get("method")}
        return adata


class _FakeAtacBackend:
    def __init__(self):
        self.last_integrate_kwargs = None

    def qc(self, adata, **kwargs):
        if kwargs.get("method") == "fragment_size":
            adata.uns["fragment_size"] = {"median": 150}
        else:
            adata.uns["qc"] = {"method": kwargs.get("method", "basic")}
        return adata

    def peak_calling(self, **kwargs):
        output_path = Path(kwargs["output_peaks_path"])
        output_path.write_text("chr1\t1\t100\tpeak1\n", encoding="utf-8")
        return PeakCallResult(method=kwargs["method"], peaks_path=output_path, n_peaks=1)

    def feature_matrix(self, adata, **kwargs):
        adata.uns["feature_matrix"] = {"method": kwargs.get("method", "peaks")}
        return adata

    def tfidf_lsi(self, adata, **kwargs):
        adata.obsm["X_lsi"] = [[0.0, 0.1], [0.2, 0.3], [0.4, 0.5]]
        adata.uns["tfidf_lsi"] = {"method": kwargs.get("method", "tfidf_lsi_v3")}
        return adata

    def integrate(self, adata, **kwargs):
        self.last_integrate_kwargs = kwargs
        embedding_key = kwargs.get("embedding_key", "X_lsi")
        output_key = "X_harmony_lsi" if embedding_key == "X_lsi" else f"{embedding_key}_harmony"
        adata.obsm[output_key] = [[0.0, 0.1], [0.2, 0.3], [0.4, 0.5]]
        adata.uns["batch_integration"] = {"method": kwargs.get("method", "harmony")}
        return adata

    def cluster(self, adata, **kwargs):
        cluster_key = kwargs.get("cluster_key") or f"{kwargs['embedding_key'].replace('X_', '')}_clusters"
        adata.obs[cluster_key] = ["0", "1", "0"]
        return adata

    def differential_accessibility(self, adata, **kwargs):
        return DEResult(
            method=kwargs["method"],
            group_key=kwargs["group_key"],
            n_groups=2,
            n_genes=adata.n_vars,
            top_per_group={"0": ["chr1:1-100"]},
        )

    def trajectory(self, adata, **kwargs):
        adata.uns["trajectory"] = {"method": kwargs.get("method", "paga")}
        return adata

    def peak_to_gene_linking(self, adata, **kwargs):
        return LinkSet(method=kwargs["method"], n_links=1, metadata={"max_distance": kwargs.get("max_distance")})

    def annotate(self, adata, **kwargs):
        group_key = kwargs.get("group_key") or "lsi_clusters"
        annotation_key = kwargs.get("annotation_key") or f"{group_key}_celltype"
        adata.obs[annotation_key] = ["T cell", "B cell", "T cell"]
        adata.uns["annotation"] = {"method": kwargs.get("method")}
        return adata


class _FakeRefs:
    def list_available(self, category=None):
        return []


class _FakeSingleCellBackend:
    refs = _FakeRefs()
    api = {}
    rna = _FakeRnaBackend()
    atac = _FakeAtacBackend()
    multi = types.SimpleNamespace()

    def read_dataset_summary(self):
        return {"dataset_summary": "fake dataset", "label_column": "cell_type"}

    def read_label_distribution(self, label_key):
        return {"label_key": label_key, "distribution": []}

    def read_prior_resource_summary(self):
        return {}

    def check_prior_coverage(self, resource_name):
        return {"resource_name": resource_name}

    def query_marker_database(self, tissue, species):
        return {"tissue": tissue, "species": species, "markers_by_cell_type": {}}

    def query_pathway_database(self, database, gene):
        return {"database": database, "gene": gene, "matches": []}

    def health_check(self):
        return {"optuna_available": True, "pipelines": ["rna_preprocess_and_cluster"]}


class AgentLayerTests(unittest.TestCase):
    def test_read_dataset_summary_inspects_h5ad_structure(self):
        class _Frame:
            def __init__(self, columns):
                self.columns = columns

        class _Array:
            shape = (3, 2)
            dtype = "float32"

        class _Context:
            feat_stats = "PBMC dataset"
            label_column = "cell_type"
            data_mod1_path = "/tmp/pbmc.h5ad"

            def _load_any(self, path):
                adata = types.SimpleNamespace(
                    n_obs=3,
                    n_vars=2,
                    X=_Array(),
                    obs=_Frame(["cell_type", "batch", "leiden"]),
                    var=_Frame(["gene_ids"]),
                    layers={"counts": _Array()},
                    obsm={"X_pca": _Array()},
                    varm={},
                    uns={"neighbors": {}},
                )
                return {"type": "h5ad", "obj": adata}

        summary = read_dataset_summary(_Context())

        self.assertEqual(summary["dataset_summary"], "PBMC dataset")
        self.assertEqual(summary["label_column"], "cell_type")
        self.assertEqual(summary["n_cells"], 3)
        self.assertEqual(summary["n_genes"], 2)
        self.assertEqual(summary["obs_columns"], ["cell_type", "batch", "leiden"])
        self.assertEqual(summary["layers"]["counts"], [3, 2])
        self.assertEqual(summary["obsm"]["X_pca"], [3, 2])
        self.assertIn("leiden", summary["cluster_or_annotation_columns"])

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
            store = PaperBackend(rag_agent=rag_agent, config=_FakeConfig(), prepared_contexts=prepared_contexts)
            distribution = store.read_label_distribution("cell_type")
            self.assertEqual(distribution["distribution"][0]["label"], "T")
            summary = store.read_paper_summary("pmc:1")
            self.assertEqual(summary["summary"]["objective"], "obj")
            section = store.fetch_paper_section("pmc:1", "methods", top_n_chunks=2)
            self.assertEqual(len(section["chunks"]), 2)
            hits = store.search_index("PBMC benchmark", "benchmark", top_k=1)
            self.assertEqual(hits["results"][0]["paper_id"], "pmc:1")

    def test_tool_registry_keeps_specs_and_executor_in_sync(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rag_agent = _FakeRagAgent(Path(tmpdir))
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
            store = PaperBackend(rag_agent=rag_agent, config=_FakeConfig(), prepared_contexts=prepared_contexts)
            registry = build_tool_registry(store)
            specs = registry.tool_specs()
            executor = registry.executor()

            spec_names = {spec["name"] for spec in specs}
            self.assertEqual(spec_names, set(executor.keys()))
            self.assertIn("search_index", spec_names)
            result = executor["search_index"](query="PBMC benchmark", channel="benchmark", top_k=1)
            self.assertEqual(result["results"][0]["paper_id"], "pmc:1")

    def test_analyst_registry_exposes_paper_and_backend_inspection_tools_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rag_agent = _FakeRagAgent(Path(tmpdir))
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
            store = PaperBackend(rag_agent=rag_agent, config=_FakeConfig(), prepared_contexts=prepared_contexts)
            registry = build_analyst_registry(store, backend=_FakeSingleCellBackend())
            names = set(registry.executor().keys())
            self.assertIn("search_index", names)
            self.assertIn("read_dataset_summary", names)
            self.assertNotIn("rna_preprocess", names)
            self.assertNotIn("rna_dimensionality_reduction", names)
            self.assertNotIn("rna_clustering", names)
            self.assertNotIn("rna_celltype_annotation", names)
            self.assertNotIn("rna_batch_integration", names)

    def test_consultant_registry_exposes_single_cell_backend_tools_when_backend_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rag_agent = _FakeRagAgent(Path(tmpdir))
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
            store = PaperBackend(rag_agent=rag_agent, config=_FakeConfig(), prepared_contexts=prepared_contexts)
            registry = build_consultant_registry(store, backend=_FakeSingleCellBackend())
            names = set(registry.executor().keys())
            self.assertIn("search_index", names)
            self.assertIn("read_dataset_summary", names)
            self.assertIn("rna_preprocess", names)
            self.assertIn("rna_dimensionality_reduction", names)
            self.assertIn("rna_clustering", names)
            self.assertIn("rna_celltype_annotation", names)
            self.assertIn("rna_batch_integration", names)

    def test_tool_consultant_registry_matches_executor_surface_and_omits_rag_search_tools(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rag_agent = _FakeRagAgent(Path(tmpdir))
            prepared_contexts = {
                "benchmark": {
                    "documents": [],
                    "session_key": "sess",
                    "collection_name": "runtime_benchmark",
                }
            }
            registry = build_tool_consultant_registry(_FakeSingleCellBackend())
            names = set(registry.executor().keys())
            self.assertIn("read_dataset_summary", names)
            self.assertIn("rna_preprocess", names)
            self.assertNotIn("search_index", names)
            self.assertNotIn("read_paper_summary", names)
            self.assertNotIn("fetch_paper_section", names)
            self.assertEqual(names, set(build_tool_executor_registry(_FakeSingleCellBackend()).executor().keys()))

    def test_tool_consultant_returns_valid_composable_dag_decision(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ToolConsultantAgent(
                engine_name="gpt-test",
                result_dir=tmpdir,
                backend=_FakeSingleCellBackend(),
                client=_FakeClient(
                    [
                        _FakeResponse(
                            "r1",
                            output=[{"type": "message", "content": [{"type": "output_text", "text": json.dumps({
                                "ignored": True
                            })}]}],
                            output_text=(
                                "<TOOL_DECISION>\n"
                                + json.dumps(
                                    {
                                        "task": "cell_type_annotation",
                                        "objective_name": "cell_type_annotation_default",
                                        "reason": "Existing RNA tools can run the workflow.",
                                        "dag_plan": {
                                            "input_h5ad_path": "/tmp/in.h5ad",
                                            "objective_name": "cell_type_annotation_default",
                                            "evaluation": {
                                                "metrics": ["ari", "nmi", "silhouette"],
                                                "embedding_key": "X_pca",
                                                "cluster_key": "$L0.cluster_key",
                                            },
                                            "layers": [
                                                {
                                                    "stage": "rna_clustering",
                                                    "variants": [
                                                        {
                                                            "method": "leiden",
                                                            "params": {"embedding_key": "X_pca"},
                                                            "declared_outputs": {"cluster_key": "pca_clusters"},
                                                        }
                                                    ],
                                                }
                                            ],
                                        },
                                        "implementation_plan": None,
                                        "research_brief": None,
                                    }
                                )
                                + "\n</TOOL_DECISION>"
                            ),
                        )
                    ]
                ),
            )
            result = agent.decide(user_message="run clustering", session_state={"input_h5ad_path": "/tmp/in.h5ad"}, session_tag="tool_consultant_test")
            self.assertIsNotNone(result["dag_plan"])
            artifact = Path(tmpdir) / "feedback" / "tool_consultant_test_decision.json"
            self.assertTrue(artifact.exists())

    def test_tool_consultant_retries_when_dag_params_include_executor_io(self):
        invalid_payload = {
            "task": "bad IO params",
            "reason": "invalid",
            "dag_plan": {
                "input_h5ad_path": "/tmp/in.h5ad",
                "layers": [
                    {
                        "stage": "rna_dimensionality_reduction",
                        "variants": [
                            {
                                "method": "seurat_pca",
                                "params": {"input_h5ad_path": "/tmp/in.h5ad", "output_h5ad_path": "/tmp/out.h5ad"},
                                "declared_outputs": {"embedding_key": "X_seurat_pca"},
                            }
                        ],
                    }
                ],
            },
            "implementation_plan": None,
            "research_brief": None,
        }
        valid_payload = {
            "task": "valid params",
            "reason": "valid",
            "dag_plan": {
                "input_h5ad_path": "/tmp/in.h5ad",
                "layers": [
                    {
                        "stage": "rna_dimensionality_reduction",
                        "variants": [
                            {
                                "method": "seurat_pca",
                                "params": {"n_pcs": 30},
                                "declared_outputs": {"embedding_key": "X_seurat_pca"},
                            }
                        ],
                    }
                ],
            },
            "implementation_plan": None,
            "research_brief": None,
        }
        client = _FakeClient(
            [
                _FakeResponse("r1", output_text="<TOOL_DECISION>\n" + json.dumps(invalid_payload) + "\n</TOOL_DECISION>"),
                _FakeResponse("r2", output_text="<TOOL_DECISION>\n" + json.dumps(valid_payload) + "\n</TOOL_DECISION>"),
            ]
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ToolConsultantAgent(
                engine_name="gpt-test",
                result_dir=tmpdir,
                backend=_FakeSingleCellBackend(),
                client=client,
            )
            result = agent.decide(
                user_message="run Seurat PCA",
                session_state={"input_h5ad_path": "/tmp/in.h5ad"},
                session_tag="tool_consultant_retry",
            )

        self.assertEqual(len(client.responses.calls), 2)
        self.assertEqual(result["dag_plan"]["layers"][0]["variants"][0]["params"], {"n_pcs": 30})
        self.assertIn("executor-managed key", client.responses.calls[1]["input"][0]["content"])

    def test_toolkits_register_into_shared_registry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rag_agent = _FakeRagAgent(Path(tmpdir))
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
            store = PaperBackend(rag_agent=rag_agent, config=_FakeConfig(), prepared_contexts=prepared_contexts)
            from agents.tool_base import AgentToolRegistry

            registry = AgentToolRegistry()
            PaperToolkit(store).register_tools(registry)
            before = set(registry.executor().keys())
            RnaComputeToolkit(_FakeSingleCellBackend()).register_tools(registry)
            after = set(registry.executor().keys())
            self.assertGreater(len(after), len(before))
            self.assertIn("search_index", after)
            self.assertIn("rna_preprocess", after)

    def test_rna_compute_toolkit_registers_single_cell_tools_when_backend_present(self):
        from agents.tool_base import AgentToolRegistry

        registry = AgentToolRegistry()
        RnaComputeToolkit(_FakeSingleCellBackend()).register_tools(registry)
        self.assertIn("rna_preprocess", registry.executor())
        self.assertIn("rna_dimensionality_reduction", registry.executor())
        self.assertIn("rna_clustering", registry.executor())
        self.assertIn("rna_celltype_annotation", registry.executor())
        self.assertIn("rna_batch_integration", registry.executor())
        result = registry.executor()["rna_clustering"](
            input_h5ad_path="/tmp/in.h5ad",
            output_h5ad_path="/tmp/out.h5ad",
            embedding_key="X_pca",
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["cluster_key"], "pca_clusters")

    def test_atac_compute_toolkit_registers_implemented_tools(self):
        from agents.tool_base import AgentToolRegistry

        backend = _FakeSingleCellBackend()
        registry = AgentToolRegistry()
        AtacComputeToolkit(backend).register_tools(registry)
        executor = registry.executor()

        with tempfile.TemporaryDirectory() as tmpdir:
            out = str(Path(tmpdir) / "out.h5ad")
            result = executor["atac_tfidf_lsi"](
                input_h5ad_path="/tmp/in.h5ad",
                output_h5ad_path=out,
                method="tfidf_lsi_v3",
            )
            self.assertEqual(result["status"], "ok")
            self.assertIn("X_lsi", result["available_embeddings"])

            result = executor["atac_clustering"](
                input_h5ad_path="/tmp/in.h5ad",
                output_h5ad_path=out,
                embedding_key="X_lsi",
            )
            self.assertEqual(result["cluster_key"], "lsi_clusters")

            result = executor["atac_batch_integration"](
                input_h5ad_path="/tmp/in.h5ad",
                output_h5ad_path=out,
                method="harmony",
                batch_key="batch",
            )
            self.assertIn("X_harmony_lsi", result["available_embeddings"])
            self.assertEqual(backend.atac.last_integrate_kwargs["embedding_key"], "X_lsi")

            result = executor["atac_differential_accessibility"](
                input_h5ad_path="/tmp/in.h5ad",
                group_key="lsi_clusters",
                method="wilcoxon",
            )
            self.assertEqual(result["top_per_group"], {"0": ["chr1:1-100"]})

            result = executor["atac_trajectory_inference"](
                input_h5ad_path="/tmp/in.h5ad",
                output_h5ad_path=out,
                method="paga",
            )
            self.assertEqual(result["status"], "ok")

            result = executor["atac_peak_to_gene_linking"](
                input_h5ad_path="/tmp/in.h5ad",
                method="peak2gene",
                max_distance=1000,
            )
            self.assertEqual(result["n_links"], 1)
            self.assertEqual(result["metadata"]["max_distance"], 1000)

            result = executor["atac_celltype_annotation"](
                input_h5ad_path="/tmp/in.h5ad",
                output_h5ad_path=out,
                method="marker_peaks",
                group_key="lsi_clusters",
                marker_peak_sets={"T cell": ["chr1:1-100"]},
            )
            self.assertEqual(result["status"], "ok")

    def test_scaffolded_compute_tool_specs_are_marked_not_implemented(self):
        from agents.tool_base import AgentToolRegistry

        registry = AgentToolRegistry()
        RnaComputeToolkit(_FakeSingleCellBackend()).register_tools(registry)
        AtacComputeToolkit(_FakeSingleCellBackend()).register_tools(registry)
        MultimodalComputeToolkit(_FakeSingleCellBackend()).register_tools(registry)
        specs = {spec["name"]: spec for spec in registry.tool_specs()}

        self.assertIn("NOT YET IMPLEMENTED", specs["rna_gene_program_inference"]["description"])
        self.assertNotIn("NOT YET IMPLEMENTED", specs["atac_tfidf_lsi"]["description"])
        self.assertIn("NOT YET IMPLEMENTED", specs["atac_gene_activity_score"]["description"])
        self.assertIn("NOT YET IMPLEMENTED", specs["multi_paired_integration"]["description"])

    def test_objective_scores_cell_type_annotation_default(self):
        score = score_metrics(
            "cell_type_annotation_default",
            {"ari": 0.8, "nmi": 0.6, "silhouette": 0.2},
        )
        self.assertAlmostEqual(score, 0.4 * 0.8 + 0.4 * 0.6 + 0.2 * 0.6)

    def test_role_specific_registries_are_separated(self):
        backend = _FakeSingleCellBackend()
        executor_names = set(build_tool_executor_registry(backend).executor().keys())
        self.assertIn("rna_clustering", executor_names)
        self.assertIn("read_dataset_summary", executor_names)


    def test_rna_batch_integration_tool_accepts_embedding_key(self):
        backend = _FakeSingleCellBackend()
        executor = build_tool_executor_registry(backend).executor()

        result = executor["rna_batch_integration"](
            input_h5ad_path="/tmp/in.h5ad",
            output_h5ad_path="/tmp/out.h5ad",
            method="harmony",
            batch_key="batch",
            embedding_key="X_seurat_pca",
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(backend.rna.last_integrate_kwargs["embedding_key"], "X_seurat_pca")
        self.assertIn("X_seurat_pca_harmony", result["available_embeddings"])

    def test_rna_dimensionality_reduction_fails_when_promised_embedding_missing(self):
        class _BadRnaBackend(_FakeRnaBackend):
            def embed(self, adata, **kwargs):
                return adata

        backend = _FakeSingleCellBackend()
        backend.rna = _BadRnaBackend()
        executor = build_tool_executor_registry(backend).executor()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "out.h5ad"
            with self.assertRaisesRegex(ValueError, "X_seurat_pca"):
                executor["rna_dimensionality_reduction"](
                    input_h5ad_path="/tmp/in.h5ad",
                    output_h5ad_path=str(output_path),
                    method="seurat_pca",
                )
            self.assertFalse(output_path.exists())

    def test_rna_annotation_fails_when_promised_label_column_missing(self):
        class _BadRnaBackend(_FakeRnaBackend):
            def annotate(self, adata, **kwargs):
                return adata

        backend = _FakeSingleCellBackend()
        backend.rna = _BadRnaBackend()
        executor = build_tool_executor_registry(backend).executor()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "out.h5ad"
            with self.assertRaisesRegex(ValueError, "pca_clusters_celltype"):
                executor["rna_celltype_annotation"](
                    input_h5ad_path="/tmp/in.h5ad",
                    output_h5ad_path=str(output_path),
                    method="cellmarker",
                    obs_cluster="pca_clusters",
                    species="human",
                    tissue_type="blood",
                )
            self.assertFalse(output_path.exists())

    def test_multimodal_integration_fails_when_backend_returns_unwritable_object(self):
        class _BadMultiBackend:
            def paired_integrate(self, rna, atac, **kwargs):
                return types.SimpleNamespace()

        backend = _FakeSingleCellBackend()
        backend.multi = _BadMultiBackend()
        executor = build_tool_executor_registry(backend).executor()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "out.h5mu"
            with self.assertRaisesRegex(ValueError, "write_h5mu/write_h5ad"):
                executor["multi_paired_integration"](
                    rna_input_h5ad_path="/tmp/rna.h5ad",
                    atac_input_h5ad_path="/tmp/atac.h5ad",
                    output_h5ad_path=str(output_path),
                    method="wnn",
                )
            self.assertFalse(output_path.exists())

    def test_tool_consultant_prompt_and_docs_use_conservative_qc_default(self):
        from prompts.tool_consultant_prompts import TOOL_CONSULTANT_DECISION_PROMPT

        docs = Path("docs/tool_docs_draft.md").read_text(encoding="utf-8")
        self.assertIn("max_pct_mito=20.0", TOOL_CONSULTANT_DECISION_PROMPT)
        self.assertIn("max_pct_mito=20.0", docs)
        self.assertIn("use max_pct_mito=5.0 only", docs.lower())

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

    def test_scran_wrapper_uses_r_runner_and_sets_uns(self):
        class _Runner:
            def __init__(self):
                self.calls = []

            def run_script(self, script_name, args, returns="json", timeout=3600):
                self.calls.append({"script_name": script_name, "args": args, "returns": returns})
                Path(args["output_matrix"]).write_text("normalized", encoding="utf-8")
                return {"status": "ok"}

        class _RunnerSuite:
            def __init__(self):
                self.r = _Runner()

        class _Adata:
            def __init__(self):
                self.layers = {"counts": "raw_counts"}
                self.uns = {}
                self.X = "old_x"

            def write_h5ad(self, path):
                Path(path).write_text("input", encoding="utf-8")

            def copy(self):
                copied = _Adata()
                copied.layers = dict(self.layers)
                copied.uns = dict(self.uns)
                copied.X = self.X
                return copied

        with mock.patch.object(rna_normalization, "_write_r_count_matrix_inputs") as write_inputs, \
                mock.patch.object(rna_normalization, "_read_cells_by_genes_matrix", return_value="normalized_x"):
            result = rna_normalization._run_scran(_Adata(), runners=_RunnerSuite())

        self.assertEqual(write_inputs.call_args.kwargs["method"], "scran")
        self.assertEqual(result.uns["normalization"]["method"], "scran")
        self.assertEqual(result.layers["counts"], "raw_counts")
        self.assertEqual(result.X, "normalized_x")

    def test_r_normalization_wrapper_passes_explicit_count_exports(self):
        class _Runner:
            def __init__(self):
                self.calls = []

            def run_script(self, script_name, args, returns="json", timeout=3600):
                self.calls.append({"script_name": script_name, "args": args, "returns": returns})
                Path(args["output_matrix"]).write_text("normalized", encoding="utf-8")
                return {"status": "ok"}

        class _RunnerSuite:
            def __init__(self):
                self.r = _Runner()

        class _Adata:
            layers = {"counts": "raw_counts"}
            uns = {}
            X = "old_x"
            var_names = ["g1"]
            obs_names = ["c1"]

            def copy(self):
                copied = _Adata()
                copied.layers = dict(self.layers)
                copied.uns = dict(self.uns)
                copied.X = self.X
                return copied

        runners = _RunnerSuite()
        with mock.patch.object(rna_normalization, "_write_r_count_matrix_inputs"), \
                mock.patch.object(rna_normalization, "_read_cells_by_genes_matrix", return_value="normalized_x"):
            rna_normalization._run_scran(_Adata(), runners=runners)

        args = runners.r.calls[0]["args"]
        self.assertIn("input_matrix", args)
        self.assertIn("input_genes", args)
        self.assertIn("input_cells", args)
        self.assertNotIn("input_h5ad", args)

    def test_seurat_v3_feature_selection_uses_counts_layer_when_available(self):
        calls = []

        class _PP:
            @staticmethod
            def highly_variable_genes(adata, **kwargs):
                calls.append(kwargs)
                adata.var["highly_variable"] = [True]

        fake_scanpy = types.SimpleNamespace(pp=_PP())
        adata = types.SimpleNamespace(layers={"counts": "raw"}, var={}, uns={})

        with mock.patch.dict(sys.modules, {"scanpy": fake_scanpy}):
            rna_feature_selection.dispatch(adata, method="seurat_v3", n_top=1)

        self.assertEqual(calls[0]["layer"], "counts")

    def test_scanvi_setup_uses_counts_layer(self):
        setup_calls = []

        class _SCANVI:
            @staticmethod
            def setup_anndata(adata, **kwargs):
                setup_calls.append(kwargs)

            def __init__(self, adata, n_latent):
                self.adata = adata
                self.n_latent = n_latent

            def train(self, **kwargs):
                pass

            def get_latent_representation(self):
                return [[0.0, 0.1]]

        fake_scvi = types.SimpleNamespace(model=types.SimpleNamespace(SCANVI=_SCANVI))
        adata = types.SimpleNamespace(
            X=types.SimpleNamespace(copy=lambda: "copied_counts"),
            layers={},
            obs={"cell_type": ["Unknown"]},
            obsm={},
            uns={},
        )

        with mock.patch.dict(sys.modules, {"scvi": fake_scvi}):
            result = rna_dimensionality_reduction._run_scanvi(adata, label_key="cell_type")

        self.assertEqual(setup_calls[0]["layer"], "counts")
        self.assertEqual(result.layers["counts"], "copied_counts")
        self.assertIn("X_scanvi", result.obsm)

    def test_scanvi_training_uses_requested_device_kwargs(self):
        train_calls = []

        class _SCANVI:
            @staticmethod
            def setup_anndata(adata, **kwargs):
                pass

            def __init__(self, adata, n_latent):
                self.adata = adata
                self.n_latent = n_latent

            def train(self, **kwargs):
                train_calls.append(kwargs)

            def get_latent_representation(self):
                return [[0.0, 0.1]]

        fake_scvi = types.SimpleNamespace(model=types.SimpleNamespace(SCANVI=_SCANVI))
        adata = types.SimpleNamespace(
            X=types.SimpleNamespace(copy=lambda: "copied_counts"),
            layers={},
            obs={"cell_type": ["Unknown"]},
            obsm={},
            uns={},
        )

        with mock.patch.dict(sys.modules, {"scvi": fake_scvi}):
            result = rna_dimensionality_reduction._run_scanvi(
                adata,
                label_key="cell_type",
                n_epochs=3,
                accelerator="mps",
                devices=1,
                precision="16-mixed",
            )

        self.assertEqual(
            train_calls[0],
            {"accelerator": "mps", "devices": 1, "precision": "16-mixed", "max_epochs": 3},
        )
        self.assertEqual(result.uns["embedding"]["training"]["accelerator"], "mps")

    def test_batch_scvi_training_normalizes_cuda_accelerator(self):
        train_calls = []

        class _SCVI:
            @staticmethod
            def setup_anndata(adata, **kwargs):
                pass

            def __init__(self, adata, n_layers, n_latent):
                self.adata = adata
                self.n_layers = n_layers
                self.n_latent = n_latent

            def train(self, **kwargs):
                train_calls.append(kwargs)

            def get_latent_representation(self):
                return [[0.0, 0.1]]

        fake_scvi = types.SimpleNamespace(model=types.SimpleNamespace(SCVI=_SCVI))
        adata = types.SimpleNamespace(
            X=types.SimpleNamespace(copy=lambda: "copied_counts"),
            layers={"counts": "raw_counts"},
            obs={"batch": ["a"]},
            obsm={},
            uns={},
        )

        with mock.patch.dict(sys.modules, {"scvi": fake_scvi}):
            result = rna_batch_integration._run_scvi(
                adata,
                batch_key="batch",
                accelerator="cuda",
                devices=1,
                n_epochs=2,
            )

        self.assertEqual(train_calls[0], {"accelerator": "gpu", "devices": 1, "max_epochs": 2})
        self.assertEqual(result.uns["batch_integration"]["training"]["accelerator"], "cuda")
        self.assertEqual(result.uns["batch_integration"]["training"]["trainer_accelerator"], "gpu")

    def test_scanorama_rejects_non_default_embedding_key(self):
        adata = types.SimpleNamespace(obs={"batch": ["a", "b"]})

        with self.assertRaisesRegex(ValueError, "integrates expression matrices"):
            rna_batch_integration.dispatch(
                adata,
                method="scanorama",
                batch_key="batch",
                embedding_key="X_custom",
            )

    def test_celltypist_uses_majority_voting_labels_when_available(self):
        class _Predictions:
            def to_adata(self):
                return types.SimpleNamespace(
                    obs={
                        "cluster": ["0", "1"],
                        "predicted_labels": types.SimpleNamespace(values=["raw_a", "raw_b"]),
                        "majority_voting": types.SimpleNamespace(values=["vote_a", "vote_b"]),
                    }
                )

        fake_celltypist = types.SimpleNamespace(annotate=lambda *args, **kwargs: _Predictions())
        adata = types.SimpleNamespace(obs={"cluster": ["0", "1"]}, uns={})

        with mock.patch.dict(sys.modules, {"celltypist": fake_celltypist}):
            rna_celltype_annotation._run_celltypist(adata, obs_cluster="cluster", majority_voting=True)

        self.assertEqual(adata.obs["cluster_celltype"], ["vote_a", "vote_b"])
        self.assertEqual(adata.uns["annotation"]["label_column"], "majority_voting")

    def test_seurat_pca_wrapper_canonicalizes_zellkonverter_embedding_alias(self):
        class _Runner:
            def run_script(self, script_name, args, returns="json", timeout=3600):
                Path(args["output_h5ad"]).write_text("seurat output", encoding="utf-8")
                return {"status": "ok", "embedding_key": "X_seurat_pca"}

        class _RunnerSuite:
            def __init__(self):
                self.r = _Runner()

        class _Adata:
            def write_h5ad(self, path):
                Path(path).write_text("input", encoding="utf-8")

        class _LoadedAdata:
            def __init__(self):
                self.obsm = {"X_X_seurat_pca": [[0.0, 0.1], [0.2, 0.3]]}
                self.uns = {}

        fake_anndata = types.SimpleNamespace(read_h5ad=lambda _path: _LoadedAdata())
        with mock.patch.dict(sys.modules, {"anndata": fake_anndata}):
            result = rna_dimensionality_reduction._run_seurat_pca(_Adata(), runners=_RunnerSuite())

        self.assertIn("X_seurat_pca", result.obsm)
        self.assertEqual(result.obsm["X_seurat_pca"], [[0.0, 0.1], [0.2, 0.3]])
        self.assertEqual(result.uns["embedding"]["obsm_key"], "X_seurat_pca")

    def test_seurat_pca_wrapper_fails_when_r_output_has_no_embedding(self):
        class _Runner:
            def run_script(self, script_name, args, returns="json", timeout=3600):
                Path(args["output_h5ad"]).write_text("seurat output", encoding="utf-8")
                return {"status": "ok", "embedding_key": "X_seurat_pca"}

        class _RunnerSuite:
            def __init__(self):
                self.r = _Runner()

        class _Adata:
            def write_h5ad(self, path):
                Path(path).write_text("input", encoding="utf-8")

        class _LoadedAdata:
            def __init__(self):
                self.obsm = {"X_umap": [[0.0, 0.1], [0.2, 0.3]]}
                self.uns = {}

        fake_anndata = types.SimpleNamespace(read_h5ad=lambda _path: _LoadedAdata())
        with mock.patch.dict(sys.modules, {"anndata": fake_anndata}):
            with self.assertRaisesRegex(RuntimeError, "Available obsm keys: \\['X_umap'\\]"):
                rna_dimensionality_reduction._run_seurat_pca(_Adata(), runners=_RunnerSuite())

    def test_seurat_pca_r_script_writes_obsm_through_anndata_not_zellkonverter(self):
        script = Path("backend/r_scripts/rna/dimreduction_seurat_pca.R").read_text(encoding="utf-8")
        write_body = script.split("write_h5ad <- function", 1)[1].split("obj <- read_h5ad", 1)[0]

        self.assertIn("ad.obsm['X_seurat_pca'] = np.asarray", write_body)
        self.assertIn("ad.write_h5ad(output_path)", write_body)
        self.assertIn("return list(check.obsm.keys())", write_body)
        self.assertNotIn("`__setitem__`", write_body)
        self.assertNotIn("zellkonverter::writeH5AD", write_body)

    def test_seurat_pca_r_script_sparse_fallback_does_not_dense_coerce_ad_x(self):
        script = Path("backend/r_scripts/rna/dimreduction_seurat_pca.R").read_text(encoding="utf-8")
        read_body = script.split("read_h5ad <- function", 1)[1].split("write_h5ad <- function", 1)[0]

        self.assertIn('ad$layers$get("counts")', read_body)
        self.assertIn("scipy_sparse$issparse(source)", read_body)
        self.assertIn("source$tocoo()", read_body)
        self.assertIn("Matrix::sparseMatrix", read_body)
        self.assertNotIn("as.matrix(ad$X)", read_body)
        self.assertNotIn("zellkonverter::readH5AD", read_body)

    def test_r_normalization_scripts_write_matrix_outputs_not_h5ad(self):
        for script_path in (
            Path("backend/r_scripts/rna/normalization_sctransform.R"),
            Path("backend/r_scripts/rna/normalization_scran.R"),
        ):
            script = script_path.read_text(encoding="utf-8")
            self.assertIn("input_matrix <- params$input_matrix", script)
            self.assertIn("Matrix::readMM", script)
            self.assertIn("write_matrix_outputs", script)
            self.assertIn("Matrix::writeMM", script)
            self.assertNotIn("readH5AD", script)
            self.assertNotIn("zellkonverter::writeH5AD", script)
            self.assertNotIn("ad$write_h5ad", script)
            self.assertNotIn("as.matrix(ad$X)", script)

    def test_seurat_pca_r_script_clamps_dimensions_for_small_inputs(self):
        script = Path("backend/r_scripts/rna/dimreduction_seurat_pca.R").read_text(encoding="utf-8")

        self.assertIn("n_features <- min(n_features, nrow(obj))", script)
        self.assertIn("n_pcs <- min(n_pcs, ncol(obj) - 1L, n_features - 1L)", script)

    def test_pseudobulk_r_scripts_filter_low_expression_genes(self):
        edger_script = Path("backend/r_scripts/rna/differential_expression_edger_pseudobulk.R").read_text(encoding="utf-8")
        deseq_script = Path("backend/r_scripts/rna/differential_expression_deseq2_pseudobulk.R").read_text(encoding="utf-8")

        self.assertIn("edgeR::filterByExpr(y, design)", edger_script)
        self.assertIn("cpm_means[rownames(tt)]", edger_script)
        self.assertIn("DESeq2::counts(dds) >= 10", deseq_script)

    def test_r_de_scripts_accept_sparse_matrix_exports_without_dense_h5ad_read(self):
        for script_path in (
            Path("backend/r_scripts/rna/differential_expression_mast.R"),
            Path("backend/r_scripts/rna/differential_expression_edger_pseudobulk.R"),
            Path("backend/r_scripts/rna/differential_expression_deseq2_pseudobulk.R"),
        ):
            script = script_path.read_text(encoding="utf-8")
            self.assertIn("input_matrix <- params$input_matrix", script)
            self.assertIn("Matrix::readMM", script)
            self.assertIn("scipy_sparse$issparse(source)", script)
            self.assertNotIn("source$toarray()", script)
            self.assertNotIn("as.matrix(reticulate::py_to_r(source))", script)
            self.assertNotIn("as.matrix(counts_sub)", script)

    def test_mast_wrapper_uses_r_runner_and_extracts_top_genes(self):
        class _Runner:
            def __init__(self):
                self.calls = []

            def run_script(self, script_name, args, returns="json", timeout=3600):
                self.calls.append({"script_name": script_name, "args": args, "returns": returns})
                Path(args["output_table"]).write_text(
                    "group,rank,gene,pval,pval_adj,lfc\n"
                    "B,1,MS4A1,1e-5,2e-5,2.1\n"
                    "B,2,CD79A,2e-5,3e-5,1.9\n"
                    "T,1,IL7R,3e-5,4e-5,2.4\n",
                    encoding="utf-8",
                )
                return {"status": "ok", "method": "mast", "group_key": "cell_type", "n_groups": 2, "n_genes": 3000}

        class _RunnerSuite:
            def __init__(self):
                self.r = _Runner()

        class _Adata:
            def __init__(self):
                self.obs = _MiniObs({"cell_type": ["B", "B", "T"]})
                self.n_vars = 3000

            def write_h5ad(self, path):
                Path(path).write_text("input", encoding="utf-8")

        with mock.patch.object(rna_differential_expression, "_write_r_de_inputs"):
            result = rna_differential_expression._run_mast(
                _Adata(),
                group_key="cell_type",
                runners=_RunnerSuite(),
                top_n=2,
            )

        self.assertEqual(result.method, "mast")
        self.assertEqual(result.n_groups, 2)
        self.assertEqual(result.top_per_group["B"], ["MS4A1", "CD79A"])
        self.assertEqual(result.top_per_group["T"], ["IL7R"])

    def test_edger_pseudobulk_wrapper_inferrs_sample_key(self):
        class _Runner:
            def __init__(self):
                self.calls = []

            def run_script(self, script_name, args, returns="json", timeout=3600):
                self.calls.append({"script_name": script_name, "args": args, "returns": returns})
                Path(args["output_table"]).write_text(
                    "group,rank,gene,pval,pval_adj,lfc\n"
                    "B,1,MS4A1,1e-5,2e-5,2.1\n",
                    encoding="utf-8",
                )
                return {
                    "status": "ok",
                    "method": "edger_pseudobulk",
                    "group_key": "cell_type",
                    "sample_key": args["sample_key"],
                    "n_groups": 1,
                    "n_genes": 3000,
                }

        class _RunnerSuite:
            def __init__(self):
                self.r = _Runner()

        class _Adata:
            def __init__(self):
                self.obs = _MiniObs(
                    {
                        "cell_type": ["B", "B", "T", "T"],
                        "sample": ["s1", "s2", "s1", "s2"],
                    }
                )
                self.n_vars = 3000

            def write_h5ad(self, path):
                Path(path).write_text("input", encoding="utf-8")

        runners = _RunnerSuite()
        with mock.patch.object(rna_differential_expression, "_write_r_de_inputs"):
            result = rna_differential_expression._run_edger_pseudobulk(
                _Adata(),
                group_key="cell_type",
                runners=runners,
                top_n=5,
            )

        self.assertEqual(runners.r.calls[0]["script_name"], "rna/differential_expression_edger_pseudobulk.R")
        self.assertEqual(runners.r.calls[0]["args"]["sample_key"], "sample")
        self.assertEqual(result.metrics["sample_key"], "sample")
        self.assertEqual(result.top_per_group["B"], ["MS4A1"])

    def test_deseq2_pseudobulk_requires_sample_axis(self):
        class _Runner:
            def run_script(self, script_name, args, returns="json", timeout=3600):
                raise AssertionError("runner should not be called without a valid sample axis")

        class _RunnerSuite:
            def __init__(self):
                self.r = _Runner()

        class _Adata:
            def __init__(self):
                self.obs = _MiniObs({"cell_type": ["B", "B", "T", "T"]})
                self.n_vars = 3000

            def write_h5ad(self, path):
                Path(path).write_text("input", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "Pseudobulk differential expression requires sample_key"):
            rna_differential_expression._run_deseq2_pseudobulk(
                _Adata(),
                group_key="cell_type",
                runners=_RunnerSuite(),
            )


if __name__ == "__main__":
    unittest.main()
