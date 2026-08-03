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


if __name__ == "__main__":
    unittest.main()
