from __future__ import annotations

import unittest

from agents.decision_schema import validate_tool_consultant_decision
from agents.research_loop import (
    ResearchLoop,
    _alignment_targets_tool_revision,
    _format_research_plan,
    _normalize_alignment_review,
)
from prompts.adversarial_prompts import ADVERSARIAL_ALIGNMENT_PROMPT
from prompts.tool_consultant_prompts import TOOL_CONSULTANT_OUTPUT_SCHEMA_PROMPT


class _FakeToolConsultant:
    def __init__(self, revised_decision):
        self.revised_decision = revised_decision
        self.calls = []

    def decide(self, *, user_message, session_state, session_tag):
        self.calls.append(
            {
                "user_message": user_message,
                "session_state": session_state,
                "session_tag": session_tag,
            }
        )
        return dict(self.revised_decision)


class _FakeAlignmentReviewer:
    def __init__(self, reviews):
        self.reviews = list(reviews)
        self.calls = []

    def review_alignment(self, *, user_question, research_plan, tool_plan, implementation_plan):
        self.calls.append(
            {
                "user_question": user_question,
                "research_plan": research_plan,
                "tool_plan": tool_plan,
                "implementation_plan": implementation_plan,
            }
        )
        return self.reviews.pop(0)


class _FakeDagExecutor:
    def __init__(self):
        self.calls = []

    def execute(self, *, dag_plan, session_tag):
        self.calls.append({"dag_plan": dag_plan, "session_tag": session_tag})
        return {
            "status": "completed",
            "best_path": {
                "resolved_outputs": {},
                "artifacts": {},
            },
        }


class ResearchLoopToolAlignmentTests(unittest.TestCase):
    def test_alignment_prompt_returns_reasoned_failure_mode_schema(self):
        self.assertIn("<ALIGNMENT_REVIEW>", ADVERSARIAL_ALIGNMENT_PROMPT)
        self.assertIn("weakest_assumption", ADVERSARIAL_ALIGNMENT_PROMPT)
        self.assertIn("missing_analysis", ADVERSARIAL_ALIGNMENT_PROMPT)
        self.assertIn("tool_mismatch", ADVERSARIAL_ALIGNMENT_PROMPT)

    def test_format_research_plan_includes_selected_plan_requirements(self):
        text = _format_research_plan(
            {
                "steps": [
                    {
                        "step_id": "step_1",
                        "biological_goal": "Determine whether chromatin leads RNA.",
                        "statistical_requirement": "Use sample-level evidence.",
                        "computational_approach": "Velocity-style lead-lag analysis.",
                    }
                ]
            },
            "Run MultiVelo and determine priming.",
            research_context={
                "concrete_analysis_claim": "Chromatin primes RNA expression.",
                "analysis_requirements": ["Define lead-lag metric."],
                "validation_requirements": ["Check peak-gene pairs."],
                "success_criteria": {"supports": "ATAC lead precedes RNA change."},
            },
        )

        self.assertIn("Concrete analysis claim: Chromatin primes RNA expression.", text)
        self.assertIn("Analysis requirements:", text)
        self.assertIn("Define lead-lag metric.", text)
        self.assertIn("Success criteria:", text)

    def test_toolconsultant_output_retention_policy_contains_semantic_types(self):
        self.assertIn("output_retention_policy", TOOL_CONSULTANT_OUTPUT_SCHEMA_PROMPT)
        self.assertIn("semantic_type", TOOL_CONSULTANT_OUTPUT_SCHEMA_PROMPT)
        self.assertIn("required_checkpoint", TOOL_CONSULTANT_OUTPUT_SCHEMA_PROMPT)

    def test_validate_tool_consultant_decision_preserves_output_retention_policy(self):
        decision = validate_tool_consultant_decision(
            {
                "task": "cluster",
                "dag_plan": {
                    "input_h5ad_path": "/tmp/input.h5ad",
                    "layers": [{"tool": "rna_quality_control", "variants": [{"method": "basic"}]}],
                },
                "implementation_plan": None,
                "research_brief": None,
                "output_retention_policy": [
                    {
                        "output_id": "qc_h5ad",
                        "semantic_type": "qc_h5ad",
                        "retention_intent": "required_checkpoint",
                        "reason": "Needed as rollback point.",
                    }
                ],
            },
            available_stages={"rna_quality_control"},
        )

        self.assertEqual(decision["output_retention_policy"][0]["semantic_type"], "qc_h5ad")

    def test_toolconsultant_revision_receives_adversarial_critique(self):
        loop = ResearchLoop.__new__(ResearchLoop)
        loop.alignment_reviewer = _FakeAlignmentReviewer(
            [
                {
                    "verdict": "needs_tool_revision",
                    "failure_mode": "tool_mismatch",
                    "target": "implementation_plan",
                    "required_revision": "Add downstream lead-lag interpretation script.",
                },
                {
                    "verdict": "survives",
                    "failure_mode": "none",
                    "target": "tool_plan",
                },
            ]
        )
        loop.tool_consultant = _FakeToolConsultant(
            {
                "dag_plan": {"layers": []},
                "implementation_plan": {"goal": "Analyze lead-lag outputs."},
                "output_retention_policy": [],
            }
        )
        loop.scientist_panel = object()
        loop.result_dir = None
        loop._save = lambda name, data: None

        revised = loop._review_and_maybe_revise_decision(
            user_question="Run MultiVelo and determine priming.",
            research_context={"selected_research_plan": {"steps": []}},
            decision={"dag_plan": {"layers": []}, "implementation_plan": None, "output_retention_policy": []},
            session_state={"input_h5ad_path": "/tmp/input.h5ad"},
            user_message="Execute selected plan.",
            phase_number=1,
        )

        self.assertEqual(len(loop.tool_consultant.calls), 1)
        call = loop.tool_consultant.calls[0]
        self.assertIn("adversarial_alignment_review", call["session_state"])
        self.assertIn("tool_mismatch", call["user_message"])
        self.assertEqual(revised["adversarial_alignment_review"]["verdict"], "survives")

    def test_alignment_review_detects_tool_revision_targets(self):
        self.assertTrue(
            _alignment_targets_tool_revision(
                {"verdict": "needs_tool_revision", "target": "implementation_plan", "failure_mode": "missing_analysis"}
            )
        )
        self.assertTrue(
            _alignment_targets_tool_revision(
                {"verdict": "needs_tool_revision", "target": "inputs_dependencies", "failure_mode": "tool_mismatch"}
            )
        )
        self.assertFalse(
            _alignment_targets_tool_revision(
                {"verdict": "blocked", "target": "inputs_dependencies", "failure_mode": "missing_analysis"}
            )
        )
        self.assertFalse(
            _alignment_targets_tool_revision(
                {"verdict": "blocked", "target": "inputs_dependencies", "failure_mode": "weak_evidence"}
            )
        )

    def test_second_alignment_review_needs_tool_revision_blocks_execution(self):
        loop = ResearchLoop.__new__(ResearchLoop)
        loop.alignment_reviewer = _FakeAlignmentReviewer(
            [
                {
                    "verdict": "needs_tool_revision",
                    "failure_mode": "tool_mismatch",
                    "target": "tool_plan",
                    "required_revision": "Fix tool mismatch.",
                },
                {
                    "verdict": "needs_tool_revision",
                    "failure_mode": "tool_mismatch",
                    "target": "tool_plan",
                    "required_revision": "Still mismatched.",
                },
            ]
        )
        loop.tool_consultant = _FakeToolConsultant(
            {
                "dag_plan": {"layers": []},
                "implementation_plan": None,
                "output_retention_policy": [],
            }
        )
        loop.scientist_panel = object()
        loop._save = lambda name, data: None

        revised = loop._review_and_maybe_revise_decision(
            user_question="Question",
            research_context={"selected_research_plan": {"steps": []}},
            decision={"dag_plan": {"layers": []}, "implementation_plan": None, "output_retention_policy": []},
            session_state={},
            user_message="Execute selected plan.",
            phase_number=1,
        )

        self.assertTrue(revised["execution_blocked"])
        self.assertTrue(revised["alignment_unresolved_after_revision"])

    def test_adversarial_remediator_prompt_uses_phase1_research_plan_schema(self):
        from prompts.adversarial_prompts import ADVERSARIAL_REMEDIATOR_PROMPT

        self.assertIn("selected_research_plan", ADVERSARIAL_REMEDIATOR_PROMPT)
        self.assertIn("alternative_research_plans", ADVERSARIAL_REMEDIATOR_PROMPT)
        self.assertIn("mediator_decision", ADVERSARIAL_REMEDIATOR_PROMPT)
        self.assertNotIn('"consensus_hypothesis"', ADVERSARIAL_REMEDIATOR_PROMPT)

    def test_execute_records_output_retention_policy_in_dag_result(self):
        loop = ResearchLoop.__new__(ResearchLoop)
        loop.dag_executor = _FakeDagExecutor()
        loop.coder = None

        result, _, status = loop._execute(
            decision={
                "dag_plan": {
                    "layers": [],
                },
                "output_retention_policy": [
                    {
                        "output_id": "clustered_h5ad",
                        "semantic_type": "clustered_h5ad",
                        "retention_intent": "required_checkpoint",
                        "reason": "Rollback point.",
                    }
                ],
                "adversarial_alignment_review": {"verdict": "survives"},
            },
            current_input_h5ad="/tmp/input.h5ad",
            phase_number=1,
        )

        self.assertEqual(status, "completed")
        self.assertEqual(result["output_retention_policy"][0]["semantic_type"], "clustered_h5ad")
        self.assertEqual(loop.dag_executor.calls[0]["dag_plan"]["output_retention_policy"][0]["output_id"], "clustered_h5ad")

    def test_normalize_alignment_review_defaults_reasoned_failure_mode(self):
        review = _normalize_alignment_review({"verdict": "bad"})
        self.assertEqual(review["verdict"], "needs_tool_revision")
        self.assertEqual(review["failure_mode"], "tool_mismatch")
        self.assertEqual(review["target"], "tool_plan")


if __name__ == "__main__":
    unittest.main()
