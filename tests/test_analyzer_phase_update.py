from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agents.analyzer_panel import _normalize_analyzer_report
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

    def test_research_loop_conclude_skips_full_panel_update(self):
        scientist = _FakeScientistPanel(
            [
                {
                    "decision": "accept_and_conclude",
                    "rationale": "Evidence is sufficient.",
                    "evidence_state": {"current_belief": "supported"},
                }
            ]
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            loop = _make_loop(tmpdir, scientist)
            result = loop.run(user_question="Answer this.", pipeline_mode="full")

        self.assertEqual(result["status"], "done")
        self.assertEqual(len(scientist.post_calls), 1)
        self.assertEqual(scientist.update_calls, [])

    def test_research_loop_uses_bounded_callbacks_instead_of_full_update(self):
        scientist = _FakeScientistPanel(
            [
                {
                    "decision": "call_panelists",
                    "rationale": "A focused callback is needed.",
                    "panelist_callback_requests": [
                        {
                            "role": "biologist",
                            "callback_type": "ask_panelist_for_more_reasoning",
                            "callback_source": "analyzer_feedback",
                            "assigned_gap": "Clarify the biology gap.",
                        }
                    ],
                },
                {
                    "decision": "accept_and_conclude",
                    "rationale": "Callback resolved the gap.",
                }
            ]
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            loop = _make_loop(tmpdir, scientist)
            result = loop.run(user_question="Answer this.", pipeline_mode="full")

        self.assertEqual(result["status"], "done")
        self.assertEqual(len(scientist.callback_calls), 1)
        self.assertEqual(scientist.update_calls, [])

    def test_research_loop_runs_targeted_callback_once_then_redecides(self):
        scientist = _FakeScientistPanel(
            [
                {
                    "decision": "call_panelists",
                    "rationale": "Need one focused gap resolved.",
                    "panelist_callback_requests": [
                        {
                            "role": "biologist",
                            "callback_type": "ask_panelist_for_more_reasoning",
                            "callback_source": "analyzer_feedback",
                            "assigned_gap": "Explain the biology gap.",
                        }
                    ],
                },
                {
                    "decision": "accept_and_conclude",
                    "rationale": "Callback resolved the gap.",
                },
            ]
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            loop = _make_loop(tmpdir, scientist)
            result = loop.run(user_question="Answer this.", pipeline_mode="full")

        self.assertEqual(result["status"], "done")
        self.assertEqual(len(scientist.post_calls), 2)
        self.assertEqual(len(scientist.callback_calls), 1)
        self.assertEqual(scientist.update_calls, [])

    def test_post_analysis_callbacks_can_run_two_bounded_rounds(self):
        scientist = _FakeScientistPanel(
            [
                {
                    "decision": "call_panelists",
                    "rationale": "Need first focused gap resolved.",
                    "panelist_callback_requests": [
                        {
                            "role": "biologist",
                            "callback_type": "ask_panelist_for_more_reasoning",
                            "callback_source": "analyzer_feedback",
                            "assigned_gap": "Explain gap one.",
                        }
                    ],
                },
                {
                    "decision": "call_panelists",
                    "rationale": "Need second focused gap resolved.",
                    "panelist_callback_requests": [
                        {
                            "role": "statistician",
                            "callback_type": "ask_panelist_for_more_reasoning",
                            "callback_source": "analyzer_feedback",
                            "assigned_gap": "Explain gap two.",
                        }
                    ],
                },
                {
                    "decision": "accept_and_conclude",
                    "rationale": "Callbacks resolved the gaps.",
                },
            ]
        )
        scientist.max_callback_rounds_after_analysis = 2
        with tempfile.TemporaryDirectory() as tmpdir:
            loop = _make_loop(tmpdir, scientist)
            result = loop.run(user_question="Answer this.", pipeline_mode="full")

        self.assertEqual(result["status"], "done")
        self.assertEqual(len(scientist.callback_calls), 2)
        self.assertEqual(len(scientist.post_calls), 3)

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

    def test_trajectory_context_injected_into_mediator_call(self):
        scientist = _FakeScientistPanel(
            [
                {
                    "decision": "accept_and_conclude",
                    "rationale": "Evidence is sufficient.",
                }
            ]
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            loop = _make_loop(tmpdir, scientist)
            loop.run(user_question="Answer this.", pipeline_mode="full")

        self.assertEqual(scientist.post_calls[0]["state_graph_context"]["active_node"]["node_id"], "plan_001")

    def test_blocked_execution_skips_analyzer_and_goes_to_mediator(self):
        scientist = _FakeScientistPanel(
            [
                {
                    "decision": "self_revise_plan",
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
                    "rationale": "Stop after the repaired phase.",
                    "evidence_state": {},
                },
            ]
        )

        class _BlockingToolConsultant(_FakeToolConsultant):
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

        with tempfile.TemporaryDirectory() as tmpdir:
            loop = _make_loop(tmpdir, scientist)
            loop.tool_consultant = _BlockingToolConsultant()
            result = loop.run(user_question="Answer this.", pipeline_mode="full")

        self.assertEqual(result["status"], "done")
        self.assertEqual(len(scientist.post_calls), 2)
        self.assertEqual(scientist.post_calls[0]["analyzer_report"]["result_verdict"], "blocked")
        self.assertEqual(scientist.post_calls[0]["analyzer_report"]["problem_localization"]["problem_stage"], "implementation_plan")
        self.assertEqual(len(loop.analyzer_panel.calls), 1)
        self.assertEqual(
            loop.tool_consultant.calls[1]["session_state"]["last_post_analysis_decision"]["decision"],
            "self_revise_plan",
        )


if __name__ == "__main__":
    unittest.main()
