import json
import sys
import tempfile
import types
import unittest
from pathlib import Path


if "numpy" not in sys.modules:
    sys.modules["numpy"] = types.ModuleType("numpy")

if "textgrad" not in sys.modules:
    fake_textgrad = types.ModuleType("textgrad")
    fake_textgrad.get_engine = lambda *args, **kwargs: None
    sys.modules["textgrad"] = fake_textgrad

if "pandas" not in sys.modules:
    sys.modules["pandas"] = types.ModuleType("pandas")


class _FakeFrame:
    def __init__(self, rows):
        self._rows = rows
        self.columns = list(rows[0].keys()) if rows else []
        self.empty = not rows


def _fake_read_csv(path, sep=","):
    with open(path, "r", encoding="utf-8") as handle:
        lines = [line.rstrip("\n") for line in handle if line.strip()]
    if not lines:
        return _FakeFrame([])
    headers = lines[0].split(sep)
    rows = []
    for line in lines[1:]:
        values = line.split(sep)
        rows.append({header: value for header, value in zip(headers, values)})
    return _FakeFrame(rows)


sys.modules["pandas"].DataFrame = getattr(sys.modules["pandas"], "DataFrame", type("DataFrame", (), {}))
sys.modules["pandas"].read_csv = _fake_read_csv
sys.modules["pandas"].ExcelFile = lambda *args, **kwargs: None
sys.modules["pandas"].read_excel = lambda *args, **kwargs: None

from pipelines.config import Config
from pipelines.evaluation_plan import compute_combined_score, normalize_evaluation_plan
from pipelines.validator import validate_stage_outputs


def sample_plan():
    return {
        "goal": "Evaluate a prior-guided single-cell pipeline with a task-aligned combined score.",
        "dataset_summary": "PBMC scRNA-seq dataset with immune populations and cell type labels available only for evaluation.",
        "query_decomposition": {
            "task_category": "clustering",
            "primary_question": "Can the pipeline learn a biologically coherent embedding for unsupervised clustering?",
            "success_hypothesis": "A useful representation improves biological coherence and cluster separation while remaining robust.",
            "expected_biological_outcome": "Immune populations separate cleanly and marker evidence aligns with known biology.",
            "benchmark_frame": "Compare against common clustering-quality and biological-coherence criteria used in recent single-cell benchmarks.",
            "key_risks": ["overclustering", "batch-driven structure"],
        },
        "guidance_per_evaluator": [
            {"evaluator_role": "biology", "what_to_look_for": "Biological coherence.", "what_good_looks_like": "Markers and summary evidence align with expected cell states."},
            {"evaluator_role": "data_science", "what_to_look_for": "Stable preprocessing.", "what_good_looks_like": "Preprocessing preserves biological signal and avoids leakage."},
            {"evaluator_role": "model", "what_to_look_for": "Representation quality.", "what_good_looks_like": "Training is stable and embeddings are useful downstream."},
            {"evaluator_role": "prior", "what_to_look_for": "Useful prior signal.", "what_good_looks_like": "Prior improves biological structure without distorting the data."},
            {"evaluator_role": "critic", "what_to_look_for": "Overall bottlenecks.", "what_good_looks_like": "Prioritized changes improve the combined optimization target."},
        ],
        "evaluation_experiments": [
            {
                "name": "cluster_quality",
                "purpose": "Assess clustering quality and biological alignment.",
                "required_metrics": ["combined_score", "silhouette", "marker_enrichment"],
                "required_summary_evidence": ["top_markers", "cluster_interpretation"],
                "priority": "high",
            }
        ],
        "expected_downstream_outputs": "Emit assignments, metrics, and biological summary evidence required to judge representation quality.",
        "downstream_requirements": {
            "required_outputs": ["cluster_assignments", "cluster_metrics", "cluster_summary"],
            "artifacts": {
                "cluster_assignments": {
                    "format": "csv",
                    "required_columns": ["cell_id", "predicted_cluster", "split", "confidence"],
                },
                "cluster_metrics": {
                    "format": "json",
                    "required_keys": ["combined_score", "silhouette", "marker_enrichment"],
                },
                "cluster_summary": {
                    "format": "json",
                    "required_keys": ["top_markers", "cluster_interpretation"],
                },
            },
        },
        "combined_metric_spec": {
            "metric_key": "combined_score",
            "direction": "maximize",
            "summary": "Weighted score across clustering quality and biological coherence.",
            "components": [
                {
                    "key": "silhouette",
                    "weight": 0.7,
                    "goal": "maximize",
                    "required": True,
                    "normalization": {"kind": "affine", "min": -1.0, "max": 1.0},
                    "rationale": "Measures cluster separation.",
                },
                {
                    "key": "marker_enrichment",
                    "weight": 0.3,
                    "goal": "maximize",
                    "required": False,
                    "normalization": {"kind": "clip", "min": 0.0, "max": 1.0},
                    "rationale": "Measures biological coherence.",
                },
            ],
            "missing_value_policy": "fail_on_required_skip_optional",
            "formula_text": "weighted normalized average over available components",
        },
    }


class EvaluationPlanTests(unittest.TestCase):
    def test_normalize_evaluation_plan_requires_critic_guidance(self):
        plan = sample_plan()
        plan["guidance_per_evaluator"] = [
            item for item in plan["guidance_per_evaluator"] if item["evaluator_role"] != "critic"
        ]
        with self.assertRaises(ValueError):
            normalize_evaluation_plan(plan)

    def test_compute_combined_score_renormalizes_optional_component(self):
        plan = normalize_evaluation_plan(sample_plan())
        score = compute_combined_score(
            {"silhouette": 0.5},
            plan["combined_metric_spec"],
        )
        expected = (0.5 - (-1.0)) / (1.0 - (-1.0))
        self.assertAlmostEqual(score, expected, places=6)

    def test_config_apply_evaluation_plan_updates_downstream_schema(self):
        cfg = Config.__new__(Config)
        cfg.current_evaluation_plan = {}
        cfg.metrics = "ari"
        cfg.apply_evaluation_plan(sample_plan())

        self.assertEqual(cfg.metrics, "combined_score")
        self.assertEqual(cfg.primary_metric_key(), "combined_score")

        downstream_schema = cfg.stage_requirements("downstream_analysis.py")
        self.assertEqual(
            downstream_schema["required_outputs"],
            ["cluster_assignments", "cluster_metrics", "cluster_summary"],
        )
        self.assertEqual(
            downstream_schema["artifacts"]["cluster_metrics"]["required_keys"],
            ["combined_score", "silhouette", "marker_enrichment"],
        )
        self.assertEqual(
            downstream_schema["evaluation_experiments"][0]["name"],
            "cluster_quality",
        )

    def test_validate_stage_outputs_accepts_recomputed_combined_score(self):
        plan = normalize_evaluation_plan(sample_plan())
        stage_schema = dict(plan["downstream_requirements"])
        stage_schema["combined_metric_spec"] = plan["combined_metric_spec"]
        stage_schema["evaluation_experiments"] = plan["evaluation_experiments"]

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            assignments_path = root / "cluster_assignments.csv"
            metrics_path = root / "cluster_metrics.json"
            summary_path = root / "cluster_summary.json"

            assignments_path.write_text(
                "cell_id,predicted_cluster,split,confidence\ncell_1,0,test,0.9\n",
                encoding="utf-8",
            )
            metrics_payload = {
                "silhouette": 0.5,
                "marker_enrichment": 0.6,
            }
            metrics_payload["combined_score"] = compute_combined_score(
                metrics_payload,
                plan["combined_metric_spec"],
            )
            metrics_path.write_text(json.dumps(metrics_payload), encoding="utf-8")
            summary_path.write_text(
                json.dumps(
                    {
                        "top_markers": {"0": ["MS4A1"]},
                        "cluster_interpretation": {"0": "B cell-like cluster"},
                    }
                ),
                encoding="utf-8",
            )

            failures = validate_stage_outputs(
                {
                    "generated_outputs": {
                        "cluster_assignments": str(assignments_path),
                        "cluster_metrics": str(metrics_path),
                        "cluster_summary": str(summary_path),
                    }
                },
                stage_schema,
                "downstream_analysis.py",
            )
            self.assertEqual(failures, [])

    def test_validate_stage_outputs_rejects_wrong_combined_score(self):
        plan = normalize_evaluation_plan(sample_plan())
        stage_schema = dict(plan["downstream_requirements"])
        stage_schema["combined_metric_spec"] = plan["combined_metric_spec"]
        stage_schema["evaluation_experiments"] = plan["evaluation_experiments"]

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            assignments_path = root / "cluster_assignments.csv"
            metrics_path = root / "cluster_metrics.json"
            summary_path = root / "cluster_summary.json"

            assignments_path.write_text(
                "cell_id,predicted_cluster,split,confidence\ncell_1,0,test,0.9\n",
                encoding="utf-8",
            )
            metrics_path.write_text(
                json.dumps(
                    {
                        "silhouette": 0.5,
                        "marker_enrichment": 0.6,
                        "combined_score": 0.123,
                    }
                ),
                encoding="utf-8",
            )
            summary_path.write_text(
                json.dumps(
                    {
                        "top_markers": {"0": ["MS4A1"]},
                        "cluster_interpretation": {"0": "B cell-like cluster"},
                    }
                ),
                encoding="utf-8",
            )

            failures = validate_stage_outputs(
                {
                    "generated_outputs": {
                        "cluster_assignments": str(assignments_path),
                        "cluster_metrics": str(metrics_path),
                        "cluster_summary": str(summary_path),
                    }
                },
                stage_schema,
                "downstream_analysis.py",
            )
            self.assertEqual(len(failures), 1)
            self.assertIn("combined_score does not match recomputed value", failures[0].message)


if __name__ == "__main__":
    unittest.main()
