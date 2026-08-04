from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agents.analyzer_panel import _normalize_analyzer_report, _summarize_dag_result
from agents.prompt_loader import load_updated_prompt
from agents.research_loop import ResearchLoop
from agents.scientist_panel import _normalize_evidence_state, _normalize_post_analysis_decision

ANALYZER_MEDIATOR_PROMPT = load_updated_prompt("analyzer")
MEDIATOR_POST_ANALYSIS_PROMPT = load_updated_prompt("mediator_post_analysis")


class _FakeScientistPanel:
    def __init__(self, post_decisions):
        self.post_decisions = list(post_decisions)
        self.formulate_calls = []
        self.post_calls = []
        self.update_calls = []
        self.callback_calls = []

    def formulate(self, *, user_question, data_summary, anchor_papers, mode):
        self.formulate_calls.append(
            {
                "user_question": user_question,
                "data_summary": data_summary,
                "anchor_papers": anchor_papers,
                "mode": mode,
            }
        )
        return {
            "concrete_analysis_claim": "Test claim.",
            "selected_research_plan": {
                "steps": [
                    {
                        "step_id": "step_1",
                        "biological_goal": "Answer the user question.",
                        "statistical_requirement": "Use valid evidence.",
                        "computational_approach": "Run a minimal DAG.",
                    }
                ],
                "required_visualizations": [],
            },
            "research_plan": {
                "steps": ["Answer the user question."],
                "required_visualizations": [],
            },
        }

    def decide_after_analysis(self, **kwargs):
        self.post_calls.append(kwargs)
        return dict(self.post_decisions.pop(0))

    def run_post_analysis_callbacks(self, **kwargs):
        self.callback_calls.append(kwargs)
        return {"selected_research_plan": kwargs["research_context"]["selected_research_plan"], "callbacks": []}

    def update(self, **kwargs):
        self.update_calls.append(kwargs)
        return {
            "next_action": "done",
            "evidence_state": {"current_belief": "done"},
            "research_plan": {},
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
        return {"dag_plan": {"layers": []}, "implementation_plan": None, "output_retention_policy": []}


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
    def __init__(self):
        self.calls = []

    def analyze(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "results_summary": "The execution produced enough evidence.",
            "claim_updates": [
                {
                    "claim_id": "C1",
                    "status": "supported",
                    "support_summary": "metric",
                    "contradicting_evidence": [],
                    "unresolved_requirements": [],
                }
            ],
            "evidence_requirement_status": [
                {
                    "requirement": "Use valid evidence.",
                    "status": "satisfied",
                    "evidence": "metric",
                    "needed_next": "",
                }
            ],
            "result_verdict": "supported",
            "problem_localization": {"problem_stage": "none", "problem_type": "none"},
        }


def _make_loop(tmpdir: str, scientist_panel: _FakeScientistPanel) -> ResearchLoop:
    loop = ResearchLoop.__new__(ResearchLoop)
    loop.scientist_panel = scientist_panel
    loop.analyzer_panel = _FakeAnalyzerPanel()
    loop.tool_consultant = _FakeToolConsultant()
    loop.alignment_reviewer = None
    loop.dag_executor = _FakeDagExecutor()
    loop.coder = None
    loop.optimizing_coder = None
    loop.attributing_critic = None
    loop.short_term_memory = None
    loop.context_manager = None
    loop.input_h5ad_path = "/tmp/input.h5ad"
    loop.data_summary = {"modality": "RNA"}
    loop.result_dir = Path(tmpdir)
    loop.result_dir.mkdir(parents=True, exist_ok=True)
    loop.max_phases = 2
    loop._prior_phase_metrics = {}
    return loop


class _LegacyScientistPanel:
    def formulate(self, *, user_question, data_summary, anchor_papers, mode):
        return {
            "selected_research_plan": {"steps": ["Run one step."], "required_visualizations": []},
            "research_plan": {"steps": ["Run one step."], "required_visualizations": []},
        }


class _LiveScientistPanel:
    """Fake panel matching the live run_initial_panelists()/MediatorAgent contract."""

    max_mediator_callback_rounds = 1
    max_callbacks_per_round = 2

    def run_initial_panelists(self, **_):
        return {
            "biologist": "bio evidence",
            "statistician": "stat evidence",
            "bioinformatician": "comp evidence",
        }

    def run_panelist_callback(self, role, callback_input):
        raise AssertionError("not expected in this test")


class _LiveMediator:
    """Fake MediatorAgent: one formulate() call, then a scripted post_analysis() per phase."""

    def __init__(self, post_decisions):
        self.post_decisions = list(post_decisions)
        self.post_contexts = []

    def formulate(self, *, formulation_context):
        return {
            "formulation_status": "ready_for_adversary",
            "selected_research_plan": {
                "plan_id": "plan_a",
                "summary": "Test plan.",
                "steps": [
                    {
                        "step_id": "step_1",
                        "biological_goal": "Answer the user question.",
                        "statistical_requirement": "Use valid evidence.",
                        "computational_approach": "Run a minimal DAG.",
                    }
                ],
                "required_visualizations": [],
            },
            "trajectory_decision": {"action": "initialize_plan", "branch_from_node_id": None, "reason": "test"},
            "evidence_state": {"analysis_claims": []},
        }

    def synthesize_callbacks(self, **_):
        raise AssertionError("not expected in this test")

    def revise_from_adversary(self, **_):
        raise AssertionError("not expected in this test")

    def post_analysis(self, *, post_analysis_context):
        self.post_contexts.append(post_analysis_context)
        return dict(self.post_decisions.pop(0))


class _LiveAdversary:
    """Fake AdversarialPanelist that always lets the candidate plan survive."""

    max_rounds = 2

    def run(self, *, adversary_context):
        return {
            "adversary_verdict": "survives",
            "verdict": "survives",
            "plan": adversary_context["candidate_plan"],
        }


class _BlockingToolConsultant(_FakeToolConsultant):
    """Blocks execution on the first phase only, to exercise the skip-analyzer path."""

    def decide(self, *, user_message, session_state, session_tag):
        super().decide(user_message=user_message, session_state=session_state, session_tag=session_tag)
        if len(self.calls) == 1:
            return {
                "dag_plan": {"layers": []},
                "implementation_plan": None,
                "output_retention_policy": [],
                "execution_blocked": True,
                "adversarial_alignment_review": {
                    "verdict": "needs_tool_revision",
                    "target": "implementation_plan",
                    "failure_mode": "missing_analysis",
                    "required_revision": "Add leakage-safe cell-level CV fallback.",
                },
            }
        return {"dag_plan": {"layers": []}, "implementation_plan": None, "output_retention_policy": []}


class AnalyzerPhaseUpdateTests(unittest.TestCase):
    def test_analyzer_prompt_and_normalizer_include_phase5_schema(self):
        self.assertIn("claim_updates", ANALYZER_MEDIATOR_PROMPT)
        self.assertIn("artifact_evidence_index", ANALYZER_MEDIATOR_PROMPT)

        report = _normalize_analyzer_report(
            {
                "results_summary": "x",
                "claim_updates": [{"claim_id": "C1", "status": "supported"}],
                "evidence_requirement_status": [{"requirement": "r", "status": "bad"}],
                "result_verdict": "bad",
                "problem_localization": {"problem_stage": "velocity", "problem_type": "missing_output"},
            }
        )

        self.assertEqual(report["result_verdict"], "supported")
        self.assertEqual(report["evidence_requirement_status"][0]["status"], "partial")
        self.assertEqual(report["problem_localization"]["problem_stage"], "velocity")

    def test_post_analysis_decision_schema_normalizes_callbacks(self):
        self.assertIn("post-analysis mode", MEDIATOR_POST_ANALYSIS_PROMPT)
        self.assertIn("<MEDIATOR_POST_ANALYSIS_OUTPUT>", MEDIATOR_POST_ANALYSIS_PROMPT)
        decision = _normalize_post_analysis_decision(
            {
                "decision": "call_panelists",
                "panelist_callbacks": {
                    "callbacks": [
                        {
                            "role": "statistician",
                            "callback_type": "ask_panelist_for_more_reasoning",
                            "callback_source": "analyzer_feedback",
                            "assigned_gap": "Is the statistical unit valid?",
                        }
                    ]
                },
                "confidence": 1.5,
            }
        )

        self.assertEqual(decision["decision_type"], "call_panelists")
        self.assertEqual(decision["callbacks"][0]["role"], "statistician")
        self.assertEqual(decision["confidence"], 1.0)

    def test_evidence_state_schema_is_enforced(self):
        evidence_state = _normalize_evidence_state(
            {
                "current_belief": "WNN remains the strongest baseline.",
                "analysis_claims": [
                    {
                        "claim_id": "C1",
                        "claim_text": "WNN is a valid baseline",
                        "status": "supported",
                        "support_summary": "metric",
                    },
                    {
                        "claim_id": "C2",
                        "claim_text": "MultiVI is mandatory",
                        "status": "bad_status",
                    },
                    {"claim_id": "C3", "claim_text": "", "status": "supported"},
                ],
                "open_questions": [
                    {"question": "Is donor grouping present?", "would_resolve": "preflight obs-key audit"}
                ],
            }
        )

        self.assertEqual(
            set(evidence_state),
            {
                "analysis_claims",
                "current_belief",
                "open_questions",
                "literature_evidence",
                "execution_evidence",
            },
        )
        self.assertEqual(evidence_state["current_belief"], "WNN remains the strongest baseline.")
        self.assertEqual(len(evidence_state["analysis_claims"]), 2)
        self.assertEqual(evidence_state["analysis_claims"][0]["status"], "supported")
        self.assertEqual(evidence_state["analysis_claims"][1]["status"], "pending")

    def test_unrecognized_decision_type_defaults_to_accept_and_conclude(self):
        # NEW-1 regression: garbled LLM response must not trigger full panel update.
        decision = _normalize_post_analysis_decision({"decision_type": "garbage_value"})
        self.assertEqual(decision["decision_type"], "accept_and_conclude")

        decision_missing = _normalize_post_analysis_decision({})
        self.assertEqual(decision_missing["decision_type"], "accept_and_conclude")

    def test_missing_post_analysis_method_concludes_without_update(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loop = _make_loop(tmpdir, _FakeScientistPanel([]))
            loop.scientist_panel = _LegacyScientistPanel()
            decision = loop._decide_after_analysis(
                user_question="Answer this.",
                phase_number=1,
                analyzer_report={"result_verdict": "supported"},
                working_model={},
                research_context={"selected_research_plan": {"steps": ["Run one step."]}},
                decision={},
                dag_result={},
            )

        self.assertEqual(decision["decision_type"], "accept_and_conclude")

    def test_blocked_execution_skips_analyzer_and_carries_decision_to_next_phase(self):
        """Live-path regression: execution_status == "blocked" must skip AnalyzerPanel
        and synthesize a _blocked_execution_report() instead (research_loop.py
        ~line 359-364), and the resulting post-analysis decision must be carried
        into the next phase's ToolConsultant session_state as
        last_post_analysis_decision (research_loop.py ~line 548 / 1093-1094).
        """
        mediator = _LiveMediator(
            [
                {
                    "decision": "self_revise_plan",
                    "decision_type": "self_revise_plan",
                    "rationale": "The adversarial critique blocks execution and must be repaired before analysis.",
                    "updated_selected_research_plan": {
                        "steps": [
                            {
                                "step_id": "step_1_revised",
                                "biological_goal": "Answer the user question.",
                                "statistical_requirement": "Use valid evidence.",
                                "computational_approach": "Add leakage-safe cell-level CV fallback.",
                            }
                        ],
                        "required_visualizations": [],
                    },
                    "evidence_state": {},
                },
                {
                    "decision": "accept_and_conclude",
                    "decision_type": "accept_and_conclude",
                    "rationale": "Stop after the repaired phase.",
                    "evidence_state": {},
                },
            ]
        )
        adversary = _LiveAdversary()
        tool_consultant = _BlockingToolConsultant()
        analyzer_panel = _FakeAnalyzerPanel()

        with tempfile.TemporaryDirectory() as tmpdir:
            loop = _make_loop(tmpdir, _LiveScientistPanel())
            loop.analyzer_panel = analyzer_panel
            loop.tool_consultant = tool_consultant
            loop.mediator_agent = mediator
            loop.adversarial_panelist = adversary
            result = loop.run(user_question="Answer this.", pipeline_mode="full")

        self.assertEqual(result["status"], "done")

        # Phase 1's execution was blocked, so AnalyzerPanel must be skipped for it;
        # only phase 2 (unblocked) invokes it.
        self.assertEqual(len(analyzer_panel.calls), 1)

        # Mediator.post_analysis() still receives a blocked-shaped analyzer_report
        # (from _blocked_execution_report), not a real AnalyzerPanel report.
        self.assertEqual(len(mediator.post_contexts), 2)
        self.assertEqual(mediator.post_contexts[0]["analyzer_report"]["result_verdict"], "blocked")
        self.assertEqual(
            mediator.post_contexts[0]["analyzer_report"]["problem_localization"]["problem_stage"],
            "implementation_plan",
        )

        # Phase 1's post-analysis decision (self_revise_plan) must be carried into
        # phase 2's ToolConsultant session_state as last_post_analysis_decision.
        self.assertEqual(
            tool_consultant.calls[1]["session_state"]["last_post_analysis_decision"]["decision"],
            "self_revise_plan",
        )


class SummarizeDagResultEvalMetricsTests(unittest.TestCase):
    """`DagExecutor._format_result` puts computed eval metrics in
    best_path["metrics"] and the ranking value in best_path["objective_score"]
    (agents/dag_executor.py ~lines 279-289). `_summarize_dag_result` must pass
    those through to the analyzer panelists — that's exactly what they're
    supposed to interpret — instead of silently dropping them."""

    def test_summary_includes_best_path_metrics_and_objective_score(self):
        dag_result = {
            "status": "completed",
            "best_path": {
                "path_index": 0,
                "config": [],
                "metrics": {"ARI": 0.8},
                "objective_score": 0.8,
                "path_dir": "/tmp/path0",
                "artifacts": {"umap": "/tmp/umap.png"},
                "stage_results": [],
                "cache_hits": [],
                "resolved_outputs": {},
            },
        }

        summary = _summarize_dag_result(dag_result)

        self.assertEqual(summary["best_path"]["metrics"], {"ARI": 0.8})
        self.assertEqual(summary["best_path"]["objective_score"], 0.8)
        self.assertNotIn("status", summary["best_path"])


if __name__ == "__main__":
    unittest.main()
