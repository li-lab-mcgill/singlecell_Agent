import unittest

from agents.prompt_loader import load_updated_prompt
from agents.scientist_panel import _normalize_research_plan_schema
from prompts.session_router_prompts import SESSION_ROUTER_PROMPT, SESSION_ROUTER_SCHEMA_PROMPT

MEDIATOR_FORMULATION_PROMPT = load_updated_prompt("mediator_formulation")
MEDIATOR_SHARED_SYSTEM = load_updated_prompt("mediator_shared_system")
PANELIST_SHARED_SYSTEM = load_updated_prompt("panelist_shared_system")


class MediatorPromptModeTests(unittest.TestCase):
    def test_mediator_schema_contains_evidence_and_novelty_fields(self):
        self.assertIn("Principal Investigator", MEDIATOR_SHARED_SYSTEM)
        self.assertIn("two timelines", MEDIATOR_SHARED_SYSTEM)
        self.assertIn("strongest current research direction", MEDIATOR_SHARED_SYSTEM)
        self.assertIn("formulation mode", MEDIATOR_FORMULATION_PROMPT)
        self.assertIn("analysis_claims", MEDIATOR_FORMULATION_PROMPT)
        self.assertIn("addresses_claims", MEDIATOR_FORMULATION_PROMPT)
        self.assertIn("novel_analysis_design", MEDIATOR_FORMULATION_PROMPT)
        self.assertIn("future_research_directions", MEDIATOR_FORMULATION_PROMPT)
        self.assertIn("alternative_plans", MEDIATOR_FORMULATION_PROMPT)
        self.assertNotIn('"research_plan": {', MEDIATOR_FORMULATION_PROMPT)

    def test_panelist_prompt_contains_existing_solution_first_guideline(self):
        self.assertIn("Do not invent novelty before identifying the", PANELIST_SHARED_SYSTEM)
        self.assertIn("closest existing baseline", PANELIST_SHARED_SYSTEM)

    def test_ambiguous_route_requests_user_choice_between_two_interpretations(self):
        combined = SESSION_ROUTER_PROMPT + SESSION_ROUTER_SCHEMA_PROMPT
        self.assertIn("two concrete interpretations", combined)
        self.assertIn("operational execution", combined)
        self.assertIn("discovery/interpretive research", combined)

    def test_normalize_research_plan_schema_backfills_legacy_fields(self):
        normalized = _normalize_research_plan_schema(
            {
                "concrete_analysis_claim": "T cell abundance differs between groups.",
                "selected_research_plan": {
                    "plan_id": "plan_a",
                    "summary": "Run established abundance analysis.",
                    "steps": [{"step_id": "step_1", "biological_goal": "Compare T cell fractions"}],
                },
                "alternative_research_plans": {"summary": "Use a different abundance model later."},
                "literature_verdict": "invalid",
                "research_case": "invalid",
                "novelty_level": 99,
                "confidence": 1.4,
            }
        )

        self.assertEqual(normalized["consensus_hypothesis"], "T cell abundance differs between groups.")
        self.assertEqual(normalized["research_plan"]["plan_id"], "plan_a")
        self.assertEqual(len(normalized["research_plan"]["steps"]), 1)
        self.assertEqual(len(normalized["alternative_research_plans"]), 1)
        self.assertEqual(normalized["literature_verdict"], "partially_answered")
        self.assertEqual(normalized["research_case"], "established_method_fits")
        self.assertEqual(normalized["novelty_level"], 5)
        self.assertEqual(normalized["confidence"], 1.0)
        self.assertEqual(normalized["panel_confidence"], 1.0)

    def test_best_effort_claim_requires_clarification_flag(self):
        normalized = _normalize_research_plan_schema(
            {
                "best_effort_claim": "The user may want either execution or interpretation.",
                "selected_research_plan": {"steps": []},
                "clarification_needed": False,
            }
        )

        self.assertTrue(normalized["clarification_needed"])
        self.assertIn("best-effort", normalized["uncertainty_reason"])


if __name__ == "__main__":
    unittest.main()
