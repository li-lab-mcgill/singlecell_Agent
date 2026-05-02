import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


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


from agents.dag_executor import DagExecutor, _resolve_refs, validate_dag_plan
from agents.decision_schema import DecisionValidationError, validate_tool_consultant_decision


class _FakeRegistry:
    def __init__(self, executor):
        self._executor = executor

    def executor(self):
        return self._executor


class _FakeRuns:
    def __init__(self):
        self.completed = []
        self.failed = []

    def create_task(self, **kwargs):
        return "task_1"

    def start_trial(self, **kwargs):
        return f"trial_{len(self.completed) + len(self.failed) + 1}"

    def complete_trial(self, trial_id, *, metrics, duration_s, artifact_paths=None):
        self.completed.append(
            {
                "trial_id": trial_id,
                "metrics": metrics,
                "duration_s": duration_s,
                "artifact_paths": artifact_paths or {},
            }
        )

    def fail_trial(self, trial_id, error_message, duration_s=None):
        self.failed.append({"trial_id": trial_id, "error": error_message, "duration_s": duration_s})


class _FakeCache:
    def __init__(self):
        self.puts = []
        self.dirs = {}
        self.meta = {}

    def key(self, input_sha, stage, params):
        return f"{input_sha[:8]}:{stage}:{json.dumps(params, sort_keys=True)}"

    def has(self, key):
        return False

    def has_dir(self, key):
        return key in self.dirs

    def get_meta(self, key):
        return self.meta.get(key, {})

    def put(self, key, src_path, *, meta=None):
        self.puts.append({"key": key, "src_path": str(src_path), "meta": meta or {}})
        return Path(src_path)

    def put_dir(self, key, src_dir, *, meta=None):
        self.puts.append({"key": key, "src_dir": str(src_dir), "meta": meta or {}})
        self.dirs[key] = Path(src_dir)
        self.meta[key] = meta or {}
        return Path(src_dir)

    def restore_dir_to(self, key, dest_dir):
        source = self.dirs[key]
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        for item in source.iterdir():
            if item.is_file():
                (dest / item.name).write_bytes(item.read_bytes())
        return dest


class _FakeEval:
    def evaluate(self, input_h5ad_path, **kwargs):
        payload = json.loads(Path(input_h5ad_path).read_text(encoding="utf-8"))
        score = float(payload.get("score", 0.0))
        return types.SimpleNamespace(
            metrics={"ari": score, "nmi": score, "silhouette": score},
            warnings=[],
        )


class _FakeBackend:
    def __init__(self):
        self.runs = _FakeRuns()
        self.cache = _FakeCache()
        self.eval = _FakeEval()
        self.config = types.SimpleNamespace(keep_intermediates=False, keep_top_k_paths=3)


def _copying_tool(*, input_h5ad_path, output_h5ad_path, output_dir=None, method, **params):
    stage_dir = Path(output_dir)
    stage_dir.mkdir(parents=True, exist_ok=True)
    source = Path(input_h5ad_path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except Exception:
        payload = {"score": 0.0}
    payload["method"] = method
    payload["params"] = params
    if "score" in params:
        payload["score"] = params["score"]
    output = Path(output_h5ad_path)
    output.write_text(json.dumps(payload), encoding="utf-8")
    return {"output_h5ad_path": str(output)}


def _maybe_failing_tool(*, input_h5ad_path, output_h5ad_path, output_dir=None, method, **params):
    if params.get("fail"):
        raise RuntimeError(f"{method} failed intentionally")
    return _copying_tool(
        input_h5ad_path=input_h5ad_path,
        output_h5ad_path=output_h5ad_path,
        output_dir=output_dir,
        method=method,
        **params,
    )


def _summary_tool(*, input_h5ad_path, output_h5ad_path, output_dir=None, method, **params):
    return {
        "dataset_summary": "PBMC summary",
        "n_cells": 3,
        "n_genes": 2,
        "obs_columns": ["cell_type", "batch"],
    }


class DagExecutorTests(unittest.TestCase):
    def test_validate_rejects_path_count_above_cap(self):
        layers = [
            {"stage": "rna_quality_control", "variants": [{"method": f"m{i}"} for i in range(11)]},
            {"stage": "rna_normalization", "variants": [{"method": f"m{i}"} for i in range(10)]},
        ]
        with self.assertRaises(DecisionValidationError):
            validate_dag_plan(
                {
                    "input_h5ad_path": "/tmp/input.h5ad",
                    "objective_name": "cell_type_annotation_default",
                    "layers": layers,
                },
                available_stages={"rna_quality_control", "rna_normalization"},
            )

    def test_validate_rejects_multi_path_without_objective(self):
        with self.assertRaises(DecisionValidationError):
            validate_dag_plan(
                {
                    "input_h5ad_path": "/tmp/input.h5ad",
                    "layers": [
                        {"stage": "rna_quality_control", "variants": [{"method": "a"}, {"method": "b"}]},
                    ],
                },
                available_stages={"rna_quality_control"},
            )

    def test_validate_rejects_unknown_stage_when_available_stages_provided(self):
        with self.assertRaises(DecisionValidationError):
            validate_tool_consultant_decision(
                {
                    "task": "bad stage",
                    "dag_plan": {
                        "input_h5ad_path": "/tmp/input.h5ad",
                        "layers": [{"stage": "not_a_tool", "variants": [{"method": "basic"}]}],
                    },
                    "implementation_plan": None,
                    "research_brief": None,
                },
                available_stages={"rna_quality_control"},
            )

    def test_top_level_objective_is_used_before_dag_validation(self):
        decision = validate_tool_consultant_decision(
            {
                "task": "multi path",
                "objective_name": "cell_type_annotation_default",
                "dag_plan": {
                    "input_h5ad_path": "/tmp/input.h5ad",
                    "layers": [
                        {"stage": "rna_quality_control", "variants": [{"method": "a"}, {"method": "b"}]},
                    ],
                },
                "implementation_plan": None,
                "research_brief": None,
            },
            available_stages={"rna_quality_control"},
        )

        self.assertEqual(decision["dag_plan"]["objective_name"], "cell_type_annotation_default")

    def test_resolve_refs_uses_layer_outputs_and_recursive_declared_outputs(self):
        path_config = [
            {
                "stage": "rna_dimensionality_reduction",
                "method": "pca",
                "declared_outputs": {"embedding_key": "X_pca", "suggested_cluster_key": "pca_clusters"},
            },
            {
                "stage": "rna_clustering",
                "method": "leiden",
                "declared_outputs": {"cluster_key": "$L0.suggested_cluster_key"},
            },
        ]
        path_config[1]["declared_outputs"] = _resolve_refs(path_config[1]["declared_outputs"], path_config, 1)

        resolved = _resolve_refs({"embedding_key": "$L0.embedding_key", "cluster_key": "$L1.cluster_key"}, path_config, 2)

        self.assertEqual(resolved["embedding_key"], "X_pca")
        self.assertEqual(resolved["cluster_key"], "pca_clusters")

    def test_composable_tool_decision_accepts_dag_plus_coder(self):
        decision = validate_tool_consultant_decision(
            {
                "task": "cluster and plot",
                "reason": "DAG clusters; coder plots",
                "dag_plan": {
                    "input_h5ad_path": "/tmp/input.h5ad",
                    "layers": [
                        {"stage": "rna_quality_control", "variants": [{"method": "basic"}]},
                    ],
                },
                "implementation_plan": {
                    "goal": "Plot cluster sizes",
                    "depends_on_dag": True,
                    "inputs": {
                        "path_dir": "dag_output.path_dir",
                        "cluster_key": "dag_output.resolved_outputs.cluster_key",
                    },
                },
                "research_brief": None,
            }
        )

        self.assertIsNotNone(decision["dag_plan"])
        self.assertIsNotNone(decision["implementation_plan"])
        self.assertTrue(decision["implementation_plan"]["depends_on_dag"])

    def test_execute_ranks_best_path_and_returns_normalized_bundle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.h5ad"
            input_path.write_text(json.dumps({"score": 0.0}), encoding="utf-8")
            backend = _FakeBackend()
            tools = {
                "rna_quality_control": _copying_tool,
                "rna_clustering": _copying_tool,
            }
            with mock.patch("agents.dag_executor.build_tool_executor_registry", return_value=_FakeRegistry(tools)):
                executor = DagExecutor(backend=backend, result_dir=Path(tmpdir) / "dag")
                result = executor.execute(
                    dag_plan={
                        "input_h5ad_path": str(input_path),
                        "objective_name": "cell_type_annotation_default",
                        "evaluation": {
                            "metrics": ["ari", "nmi", "silhouette"],
                            "cluster_key": "$L1.cluster_key",
                        },
                        "layers": [
                            {
                                "stage": "rna_quality_control",
                                "variants": [
                                    {
                                        "method": "basic",
                                        "params": {},
                                        "declared_outputs": {"embedding_key": "X_pca"},
                                    }
                                ],
                            },
                            {
                                "stage": "rna_clustering",
                                "variants": [
                                    {
                                        "method": "leiden",
                                        "params": {"score": 0.2, "embedding_key": "$L0.embedding_key"},
                                        "declared_outputs": {"cluster_key": "low_clusters"},
                                    },
                                    {
                                        "method": "leiden",
                                        "params": {"score": 0.9, "embedding_key": "$L0.embedding_key"},
                                        "declared_outputs": {"cluster_key": "high_clusters"},
                                    },
                                ],
                            },
                        ],
                    },
                    session_tag="turn1",
                )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["paths_completed"], 2)
        self.assertEqual(result["best_path"]["path_index"], 1)
        self.assertEqual(result["best_path"]["resolved_outputs"]["cluster_key"], "high_clusters")
        self.assertIn("output_h5ad_path", result["best_path"]["resolved_outputs"])
        self.assertNotIn("output_h5ad_path", result["best_path"]["artifacts"])
        self.assertNotIn("$L", json.dumps(result["comparison_table"]))
        for row in result["comparison_table"]:
            self.assertEqual(row["rna_clustering_embedding_key"], "X_pca")
        self.assertEqual(len(result["comparison_table"]), 2)
        self.assertEqual(len(backend.runs.completed), 2)

    def test_single_path_dag_logs_trial_without_objective_score(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.h5ad"
            input_path.write_text(json.dumps({"score": 0.5}), encoding="utf-8")
            backend = _FakeBackend()
            tools = {"rna_clustering": _copying_tool}
            with mock.patch("agents.dag_executor.build_tool_executor_registry", return_value=_FakeRegistry(tools)):
                executor = DagExecutor(backend=backend, result_dir=Path(tmpdir) / "dag")
                result = executor.execute(
                    dag_plan={
                        "input_h5ad_path": str(input_path),
                        "evaluation": {"metrics": ["ari", "nmi", "silhouette"]},
                        "layers": [
                            {
                                "stage": "rna_clustering",
                                "variants": [{"method": "leiden", "params": {"score": 0.5}}],
                            }
                        ],
                    },
                    session_tag="single_path",
                )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["paths_completed"], 1)
        self.assertIsNone(result["best_path"]["objective_score"])
        self.assertEqual(result["comparison_table"], [])
        self.assertEqual(len(backend.runs.completed), 1)

    def test_validate_rejects_executor_managed_keys_inside_variant_params(self):
        with self.assertRaisesRegex(DecisionValidationError, "executor-managed key"):
            validate_dag_plan(
                {
                    "input_h5ad_path": "/tmp/input.h5ad",
                    "layers": [
                        {
                            "stage": "rna_dimensionality_reduction",
                            "variants": [
                                {
                                    "method": "seurat_pca",
                                    "params": {
                                        "input_h5ad_path": "/tmp/input.h5ad",
                                        "output_h5ad_path": "/tmp/out.h5ad",
                                    },
                                    "declared_outputs": {"embedding_key": "X_seurat_pca"},
                                }
                            ],
                        }
                    ],
                },
                available_stages={"rna_dimensionality_reduction"},
            )

    def test_non_h5ad_stage_result_is_preserved_for_summarizer(self):
        calls = {"read_dataset_summary": 0}

        def counted_summary_tool(**kwargs):
            calls["read_dataset_summary"] += 1
            return _summary_tool(**kwargs)

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.h5ad"
            input_path.write_text(json.dumps({"score": 0.0}), encoding="utf-8")
            backend = _FakeBackend()
            tools = {"read_dataset_summary": counted_summary_tool}
            with mock.patch("agents.dag_executor.build_tool_executor_registry", return_value=_FakeRegistry(tools)):
                executor = DagExecutor(backend=backend, result_dir=Path(tmpdir) / "dag")
                result = executor.execute(
                    dag_plan={
                        "input_h5ad_path": str(input_path),
                        "layers": [
                            {
                                "stage": "read_dataset_summary",
                                "variants": [{"method": "default"}],
                            }
                        ],
                    },
                    session_tag="summary",
                )
                cached_result = executor.execute(
                    dag_plan={
                        "input_h5ad_path": str(input_path),
                        "layers": [
                            {
                                "stage": "read_dataset_summary",
                                "variants": [{"method": "default"}],
                            }
                        ],
                    },
                    session_tag="summary_cached",
                )

        best = result["best_path"]
        self.assertEqual(best["stage_results"][0]["result"]["dataset_summary"], "PBMC summary")
        self.assertEqual(best["stage_results"][0]["result"]["n_cells"], 3)
        self.assertIn("00_read_dataset_summary/result.json", best["artifacts"])
        self.assertNotIn("output_h5ad_path", best["artifacts"])
        self.assertEqual(calls["read_dataset_summary"], 1)
        self.assertEqual(cached_result["best_path"]["cache_hits"], ["read_dataset_summary"])
        self.assertEqual(cached_result["best_path"]["stage_results"][0]["result"]["n_genes"], 2)

    def test_execute_restores_shared_prefix_from_directory_cache(self):
        calls = {"rna_quality_control": 0, "rna_clustering": 0}

        def counted_tool(**kwargs):
            calls[kwargs.pop("stage_name")] += 1
            return _copying_tool(**kwargs)

        def qc_tool(**kwargs):
            return counted_tool(stage_name="rna_quality_control", **kwargs)

        def cluster_tool(**kwargs):
            return counted_tool(stage_name="rna_clustering", **kwargs)

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.h5ad"
            input_path.write_text(json.dumps({"score": 0.0}), encoding="utf-8")
            backend = _FakeBackend()
            tools = {
                "rna_quality_control": qc_tool,
                "rna_clustering": cluster_tool,
            }
            with mock.patch("agents.dag_executor.build_tool_executor_registry", return_value=_FakeRegistry(tools)):
                executor = DagExecutor(backend=backend, result_dir=Path(tmpdir) / "dag")
                result = executor.execute(
                    dag_plan={
                        "input_h5ad_path": str(input_path),
                        "objective_name": "cell_type_annotation_default",
                        "evaluation": {"metrics": ["ari", "nmi", "silhouette"]},
                        "layers": [
                            {
                                "stage": "rna_quality_control",
                                "variants": [{"method": "basic", "params": {}}],
                            },
                            {
                                "stage": "rna_clustering",
                                "variants": [
                                    {"method": "leiden", "params": {"score": 0.1}},
                                    {"method": "leiden", "params": {"score": 0.8}},
                                ],
                            },
                        ],
                    },
                    session_tag="cached",
                )

        self.assertEqual(result["paths_completed"], 2)
        self.assertEqual(calls["rna_quality_control"], 1)
        self.assertEqual(calls["rna_clustering"], 2)
        self.assertEqual(result["comparison_table"][1]["status"], "completed")

    def test_execute_cleans_reused_path_directory_before_running(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.h5ad"
            input_path.write_text(json.dumps({"score": 0.0}), encoding="utf-8")
            result_dir = Path(tmpdir) / "dag"
            stale_file = result_dir / "reused" / "path_000" / "00_read_dataset_summary" / "result.json"
            stale_file.parent.mkdir(parents=True, exist_ok=True)
            stale_file.write_text(json.dumps({"stale": True}), encoding="utf-8")

            backend = _FakeBackend()
            tools = {"rna_quality_control": _copying_tool}
            with mock.patch("agents.dag_executor.build_tool_executor_registry", return_value=_FakeRegistry(tools)):
                executor = DagExecutor(backend=backend, result_dir=result_dir)
                result = executor.execute(
                    dag_plan={
                        "input_h5ad_path": str(input_path),
                        "evaluation": {"metrics": ["ari"]},
                        "layers": [
                            {
                                "stage": "rna_quality_control",
                                "variants": [{"method": "basic", "params": {"score": 0.8}}],
                            }
                        ],
                    },
                    session_tag="reused",
                )

            self.assertEqual(result["status"], "completed")
            self.assertFalse(stale_file.exists())
            self.assertTrue((result_dir / "reused" / "path_000" / "00_rna_quality_control" / "output.h5ad").exists())

    def test_equal_objective_scores_tie_break_to_lower_path_index(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.h5ad"
            input_path.write_text(json.dumps({"score": 0.0}), encoding="utf-8")
            backend = _FakeBackend()
            tools = {"rna_clustering": _copying_tool}
            with mock.patch("agents.dag_executor.build_tool_executor_registry", return_value=_FakeRegistry(tools)):
                executor = DagExecutor(backend=backend, result_dir=Path(tmpdir) / "dag")
                result = executor.execute(
                    dag_plan={
                        "input_h5ad_path": str(input_path),
                        "objective_name": "cell_type_annotation_default",
                        "evaluation": {"metrics": ["ari", "nmi", "silhouette"]},
                        "layers": [
                            {
                                "stage": "rna_clustering",
                                "variants": [
                                    {"method": "leiden", "params": {"score": 0.7}},
                                    {"method": "louvain", "params": {"score": 0.7}},
                                ],
                            }
                        ],
                    },
                    session_tag="tie",
                )

        self.assertEqual(result["best_path"]["path_index"], 0)
        self.assertEqual([row["path_index"] for row in result["comparison_table"]], [0, 1])

    def test_failed_path_does_not_block_successful_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.h5ad"
            input_path.write_text(json.dumps({"score": 0.0}), encoding="utf-8")
            backend = _FakeBackend()
            tools = {"rna_clustering": _maybe_failing_tool}
            with mock.patch("agents.dag_executor.build_tool_executor_registry", return_value=_FakeRegistry(tools)):
                executor = DagExecutor(backend=backend, result_dir=Path(tmpdir) / "dag")
                result = executor.execute(
                    dag_plan={
                        "input_h5ad_path": str(input_path),
                        "objective_name": "cell_type_annotation_default",
                        "evaluation": {"metrics": ["ari", "nmi", "silhouette"]},
                        "layers": [
                            {
                                "stage": "rna_clustering",
                                "variants": [
                                    {"method": "bad", "params": {"fail": True}},
                                    {"method": "good", "params": {"score": 0.9}},
                                ],
                            }
                        ],
                    },
                    session_tag="partial_paths",
                )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["paths_completed"], 1)
        self.assertEqual(result["paths_failed"], 1)
        self.assertEqual(result["best_path"]["path_index"], 1)
        failed_rows = [row for row in result["comparison_table"] if row["status"] == "failed"]
        self.assertEqual(len(failed_rows), 1)
        self.assertIn("failed intentionally", failed_rows[0]["error"])
        self.assertEqual(len(backend.runs.completed), 1)
        self.assertEqual(len(backend.runs.failed), 1)

    def test_full_annotation_dag_shape_can_enumerate_48_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.h5ad"
            input_path.write_text(json.dumps({"score": 0.0}), encoding="utf-8")
            backend = _FakeBackend()
            tools = {
                "rna_quality_control": _copying_tool,
                "rna_normalization": _copying_tool,
                "rna_dimensionality_reduction": _copying_tool,
                "rna_celltype_annotation": _copying_tool,
            }
            with mock.patch("agents.dag_executor.build_tool_executor_registry", return_value=_FakeRegistry(tools)):
                executor = DagExecutor(backend=backend, result_dir=Path(tmpdir) / "dag")
                result = executor.execute(
                    dag_plan={
                        "input_h5ad_path": str(input_path),
                        "objective_name": "cell_type_annotation_default",
                        "evaluation": {"metrics": ["ari", "nmi", "silhouette"]},
                        "layers": [
                            {
                                "stage": "rna_quality_control",
                                "variants": [
                                    {"method": "basic", "params": {"score": 0.1}},
                                    {"method": "scrublet", "params": {"score": 0.2}},
                                ],
                            },
                            {
                                "stage": "rna_normalization",
                                "variants": [
                                    {"method": "log1p", "params": {"score": 0.3}},
                                    {"method": "sctransform", "params": {"score": 0.4}},
                                    {"method": "scran", "params": {"score": 0.5}},
                                ],
                            },
                            {
                                "stage": "rna_dimensionality_reduction",
                                "variants": [
                                    {"method": "pca", "params": {"score": 0.6}},
                                    {"method": "scvi", "params": {"score": 0.7}},
                                ],
                            },
                            {
                                "stage": "rna_celltype_annotation",
                                "variants": [
                                    {"method": "celltypist", "params": {"score": 0.8}},
                                    {"method": "cellmarker", "params": {"score": 0.85}},
                                    {"method": "gpt4", "params": {"score": 0.9}},
                                    {"method": "scanvi", "params": {"score": 0.95}},
                                ],
                            },
                        ],
                    },
                    session_tag="annotation_48",
                )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["paths_completed"], 48)
        self.assertEqual(result["paths_failed"], 0)
        self.assertEqual(len(result["comparison_table"]), 48)
        self.assertEqual(result["best_path"]["config"][-1]["method"], "scanvi")

    def test_retention_keeps_top_three_final_outputs_and_deletes_intermediates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.h5ad"
            input_path.write_text(json.dumps({"score": 0.0}), encoding="utf-8")
            backend = _FakeBackend()
            tools = {
                "rna_quality_control": _copying_tool,
                "rna_clustering": _copying_tool,
            }
            with mock.patch("agents.dag_executor.build_tool_executor_registry", return_value=_FakeRegistry(tools)):
                executor = DagExecutor(backend=backend, result_dir=Path(tmpdir) / "dag")
                result = executor.execute(
                    dag_plan={
                        "input_h5ad_path": str(input_path),
                        "objective_name": "cell_type_annotation_default",
                        "evaluation": {"metrics": ["ari", "nmi", "silhouette"]},
                        "layers": [
                            {
                                "stage": "rna_quality_control",
                                "variants": [{"method": "basic", "params": {}}],
                            },
                            {
                                "stage": "rna_clustering",
                                "variants": [
                                    {"method": "leiden", "params": {"score": 0.1}},
                                    {"method": "leiden", "params": {"score": 0.2}},
                                    {"method": "leiden", "params": {"score": 0.3}},
                                    {"method": "leiden", "params": {"score": 0.4}},
                                ],
                            },
                        ],
                    },
                    session_tag="retention",
                )

            run_dir = Path(result["artifact_dir"])
            kept_outputs = sorted(run_dir.glob("path_*/01_rna_clustering/output.h5ad"))
            qc_outputs = sorted(run_dir.glob("path_*/00_rna_quality_control/output.h5ad"))

            self.assertEqual(result["best_path"]["path_index"], 3)
            self.assertEqual(result["retention_summary"]["protected_path_indices"], [1, 2, 3])
            self.assertEqual(len(kept_outputs), 3)
            self.assertEqual(qc_outputs, [])
            self.assertTrue(Path(result["best_path"]["resolved_outputs"]["output_h5ad_path"]).exists())
            self.assertTrue(Path(result["artifact_manifest_path"]).exists())

    def test_retention_keeps_intermediates_when_configured(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.h5ad"
            input_path.write_text(json.dumps({"score": 0.0}), encoding="utf-8")
            backend = _FakeBackend()
            backend.config.keep_intermediates = True
            tools = {
                "rna_quality_control": _copying_tool,
                "rna_clustering": _copying_tool,
            }
            with mock.patch("agents.dag_executor.build_tool_executor_registry", return_value=_FakeRegistry(tools)):
                executor = DagExecutor(backend=backend, result_dir=Path(tmpdir) / "dag")
                result = executor.execute(
                    dag_plan={
                        "input_h5ad_path": str(input_path),
                        "objective_name": "cell_type_annotation_default",
                        "evaluation": {"metrics": ["ari"]},
                        "layers": [
                            {"stage": "rna_quality_control", "variants": [{"method": "basic"}]},
                            {"stage": "rna_clustering", "variants": [{"method": "leiden", "params": {"score": 0.9}}]},
                        ],
                    },
                    session_tag="keep_intermediates",
                )

            self.assertTrue((Path(result["artifact_dir"]) / "path_000" / "00_rna_quality_control" / "output.h5ad").exists())
            self.assertEqual(result["retention_summary"]["deleted_files"], 0)


if __name__ == "__main__":
    unittest.main()
