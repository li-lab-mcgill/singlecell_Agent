from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agents.research_loop import ResearchLoop
from agents.short_term_memory import _describe_metric_delta, _summarize_dag_result


class _FakeScientistPanel:
    def run_initial_panelists(self, **_):
        return {
            "biologist": "bio evidence",
            "statistician": "stat evidence",
            "bioinformatician": "comp evidence",
        }

    def run_panelist_callback(self, role, callback_input):
        return {"role": role, "gap_resolved": True, "callback_input": callback_input}


class _FakeMediator:
    def __init__(self):
        self.post_contexts = []

    def formulate(self, *, formulation_context):
        return {
            "formulation_status": "ready_for_adversary",
            "concrete_analysis_claim": "Stored claim.",
            "selected_research_plan": {
                "plan_id": "plan_a",
                "summary": "Stored selected plan.",
                "steps": [
                    {
                        "step_id": "step_1",
                        "biological_goal": "Test storage.",
                        "statistical_requirement": "Valid evidence.",
                        "computational_approach": "Minimal DAG.",
                    }
                ],
                "required_visualizations": [],
            },
            "alternative_research_plans": [
                {
                    "plan_id": "plan_b",
                    "summary": "Alternative plan.",
                    "why_not_selected_now": "Not needed first.",
                }
            ],
            "trajectory_decision": {"action": "initialize_plan", "branch_from_node_id": None, "reason": "test"},
            "evidence_state": {"analysis_claims": []},
        }

    def post_analysis(self, *, post_analysis_context):
        self.post_contexts.append(post_analysis_context)
        return {
            "decision": "accept_and_conclude",
            "decision_type": "accept_and_conclude",
            "rationale": "Enough evidence.",
            "evidence_state": {"current_belief": "complete"},
        }


class _FakeAdversary:
    max_rounds = 2

    def __init__(self):
        self.contexts = []

    def run(self, *, adversary_context):
        self.contexts.append(adversary_context)
        return {
            "adversary_verdict": "survives",
            "verdict": "survives",
            "plan": adversary_context["candidate_plan"],
        }


class _FakeToolConsultant:
    def __init__(self):
        self.calls = []

    def decide(self, *, user_message, session_state, session_tag):
        self.calls.append(
            {
                "user_message": user_message,
                "session_state": session_state,
                "session_tag": session_tag,
            }
        )
        return {
            "dag_plan": {"layers": []},
            "implementation_plan": None,
            "output_retention_policy": [],
        }


class _FakeDagExecutor:
    def execute(self, *, dag_plan, session_tag):
        return {
            "status": "completed",
            "best_path": {
                "status": "completed",
                "artifacts": {},
                "resolved_outputs": {},
            },
        }


class _FakeAnalyzerPanel:
    def analyze(self, **kwargs):
        return {
            "results_summary": "Storage test completed.",
            "claim_updates": [
                {
                    "claim_id": "C1",
                    "status": "supported",
                    "support_summary": "ok",
                    "contradicting_evidence": [],
                    "unresolved_requirements": [],
                }
            ],
            "evidence_requirement_status": [{"requirement": "Valid evidence.", "status": "satisfied", "evidence": "ok"}],
            "result_verdict": "supported",
            "problem_localization": {"problem_stage": "none", "problem_type": "none"},
        }


class SessionStorageTests(unittest.TestCase):
    def test_discovery_run_creates_session_graph_and_node_refs_before_toolconsultant(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scientist = _FakeScientistPanel()
            tool_consultant = _FakeToolConsultant()
            mediator = _FakeMediator()
            adversary = _FakeAdversary()
            loop = ResearchLoop.__new__(ResearchLoop)
            loop.scientist_panel = scientist
            loop.analyzer_panel = _FakeAnalyzerPanel()
            loop.tool_consultant = tool_consultant
            loop.alignment_reviewer = None
            loop.dag_executor = _FakeDagExecutor()
            loop.coder = None
            loop.optimizing_coder = None
            loop.attributing_critic = None
            loop.short_term_memory = None
            loop.context_manager = None
            loop.input_h5ad_path = "/tmp/input.h5ad"
            loop.data_summary = {"modality": "RNA"}
            loop.result_dir = Path(tmpdir) / "legacy_results"
            loop.result_dir.mkdir(parents=True)
            loop.max_phases = 1
            loop._prior_phase_metrics = {}
            loop.session_recorder = None
            loop.state_graph_manager = None
            loop.mediator_agent = mediator
            loop.adversarial_panelist = adversary

            result = loop.run(user_question="Store this discovery run.", pipeline_mode="full")

            self.assertEqual(result["status"], "done")
            recorder = loop.session_recorder
            self.assertIsNotNone(recorder)
            session_dir = recorder.session_dir
            self.assertTrue((session_dir / "session.json").exists())
            self.assertTrue((session_dir / "state_graph.json").exists())
            self.assertTrue((session_dir / "progress.jsonl").exists())
            self.assertTrue((session_dir / "nodes" / "plan_001" / "research_plan.json").exists())
            self.assertTrue((session_dir / "nodes" / "plan_001" / "tool_plan.json").exists())
            self.assertTrue((session_dir / "nodes" / "plan_001" / "execution_summary.json").exists())
            self.assertTrue((session_dir / "nodes" / "plan_001" / "analyzer_report.json").exists())
            self.assertTrue((session_dir / "nodes" / "plan_001" / "next_decision.json").exists())
            self.assertTrue((session_dir / "executions" / "exec_001" / "dag_result.json").exists())
            self.assertTrue((session_dir / "reports" / "final_answer.json").exists())

            graph = json.loads((session_dir / "state_graph.json").read_text())
            self.assertEqual(graph["nodes"]["plan_001"]["status"], "concluded")
            self.assertEqual(graph["nodes"]["plan_002"]["role"], "alternative")

            session_state_seen = tool_consultant.calls[0]["session_state"]
            self.assertEqual(session_state_seen["state_graph_context"]["active_node"]["node_id"], "plan_001")
            self.assertEqual(mediator.post_contexts[0]["active_plan"]["node_id"], "plan_001")


class SummarizeDagResultKeysTests(unittest.TestCase):
    """`DagExecutor._format_result` produces best_path with keys `path_index`
    and `stage_results` (agents/dag_executor.py ~lines 279-286), not `path_id`
    or `stages`. `short_term_memory._summarize_dag_result` must read the keys
    DagExecutor actually emits, or every persisted phase records
    best_path_id: null and n_stages: 0."""

    def test_summary_reads_path_index_and_stage_results(self):
        dag_result = {
            "status": "completed",
            "best_path": {"path_index": 2, "stage_results": [{}, {}]},
        }

        summary = _summarize_dag_result(dag_result)

        self.assertEqual(summary["best_path_id"], 2)
        self.assertEqual(summary["n_stages"], 2)


class MetricDeltaDirectionAwareTests(unittest.TestCase):
    """`_describe_metric_delta` (agents/short_term_memory.py ~lines 290-310) must
    classify lower-is-better metrics (pct_mito, doublet_rate) by direction, not
    by raw sign of delta. Lowering pct_mito 0.10->0.05 is an improvement, but
    the naive `delta > 0` check records it as 'remained problematic'."""

    def test_pct_mito_decrease_is_improvement(self):
        improved, remained = _describe_metric_delta(
            prior_metrics={"pct_mito": 0.10},
            current_metrics={"pct_mito": 0.05},
        )
        self.assertIn("pct_mito", improved)
        self.assertNotIn("pct_mito", remained)

    def test_doublet_rate_increase_is_problematic(self):
        improved, remained = _describe_metric_delta(
            prior_metrics={"doublet_rate": 0.02},
            current_metrics={"doublet_rate": 0.05},
        )
        self.assertIn("doublet_rate", remained)
        self.assertNotIn("doublet_rate", improved)

    def test_ari_increase_is_improvement(self):
        improved, remained = _describe_metric_delta(
            prior_metrics={"ARI": 0.5},
            current_metrics={"ARI": 0.7},
        )
        self.assertIn("ARI", improved)
        self.assertNotIn("ARI", remained)

    def test_ari_decrease_is_problematic(self):
        improved, remained = _describe_metric_delta(
            prior_metrics={"ARI": 0.7},
            current_metrics={"ARI": 0.5},
        )
        self.assertIn("ARI", remained)
        self.assertNotIn("ARI", improved)

    def test_no_label_has_malformed_sign(self):
        improved, remained = _describe_metric_delta(
            prior_metrics={"pct_mito": 0.10, "doublet_rate": 0.02, "ARI": 0.5},
            current_metrics={"pct_mito": 0.05, "doublet_rate": 0.05, "ARI": 0.7},
        )
        self.assertNotIn("+-", improved)
        self.assertNotIn("+-", remained)


if __name__ == "__main__":
    unittest.main()
