import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agents.mediator_agent import MediatorAgent, _tag_done_handler
from agents.scientist_panel import _normalize_research_plan_schema
from prompts.mediator_prompts import MEDIATOR_FORMULATION_PROMPT, MEDIATOR_SHARED_SYSTEM
from prompts.panelist_prompts import PANELIST_SHARED_SYSTEM
from prompts.session_router_prompts import SESSION_ROUTER_PROMPT, SESSION_ROUTER_SCHEMA_PROMPT


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


class TagDoneHandlerAliasTests(unittest.TestCase):
    """`_tag_done_handler` must accept the same alias tags `_extract_tag_json` tolerates,
    otherwise the ToolCallingAgentRunner never sees done=True and burns through
    max_iterations before crashing with RuntimeError."""

    def test_alias_tag_is_recognized_as_done(self):
        text = '<MEDIATOR>{"formulation_status": "ready_for_adversary"}</MEDIATOR>'
        result = _tag_done_handler(text, "MEDIATOR_OUTPUT")

        self.assertEqual(result, {"done": True, "result": text})

    def test_post_analysis_alias_tag_is_recognized_as_done(self):
        text = '<POST_ANALYSIS_DECISION>{"decision": "accept_and_conclude"}</POST_ANALYSIS_DECISION>'
        result = _tag_done_handler(text, "MEDIATOR_POST_ANALYSIS_OUTPUT")

        self.assertEqual(result, {"done": True, "result": text})

    def test_canonical_tag_is_still_recognized_as_done(self):
        text = '<MEDIATOR_OUTPUT>{"formulation_status": "ready_for_adversary"}</MEDIATOR_OUTPUT>'
        result = _tag_done_handler(text, "MEDIATOR_OUTPUT")

        self.assertEqual(result, {"done": True, "result": text})

    def test_response_with_no_recognized_tag_is_not_done(self):
        text = "I am still thinking about the plan and have not produced a tagged block yet."
        result = _tag_done_handler(text, "MEDIATOR_OUTPUT")

        self.assertFalse(result["done"])
        self.assertIn("next_user_input", result)


class MediatorFastEngineRoutingTests(unittest.TestCase):
    """Task 2.3: JSON-repair retries should use the fast engine; the primary
    mediation call must stay on the main engine regardless of what fast engine
    is configured."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.result_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_fast_engine_name_defaults_to_engine_name_when_omitted(self):
        mediator = MediatorAgent(engine_name="main-engine", client=object(), result_dir=self.result_dir)
        self.assertEqual(mediator.fast_engine_name, "main-engine")

    def test_fast_engine_name_uses_explicit_override(self):
        mediator = MediatorAgent(
            engine_name="main-engine",
            fast_engine_name="fast-engine",
            client=object(),
            result_dir=self.result_dir,
        )
        self.assertEqual(mediator.fast_engine_name, "fast-engine")

    def test_json_repair_retry_uses_fast_engine_while_main_call_uses_main_engine(self):
        """Non-vacuous: the first (primary formulation) call must be tagged with
        an invalid formulation_status so the repair path is actually reached,
        proving the two calls really are routed to different engines rather
        than both being satisfied by the first response."""
        captured_models: list[str] = []

        def fake_single_llm_call(client, model, prompt, *, system=""):
            captured_models.append(model)
            if len(captured_models) == 1:
                # Primary mediation call: deliberately invalid so validation
                # fails and the schema-repair retry is triggered.
                return '<MEDIATOR_OUTPUT>{"formulation_status": "not_a_real_status"}</MEDIATOR_OUTPUT>'
            # Schema-repair retry: valid output.
            return (
                '<MEDIATOR_OUTPUT>{"formulation_status": "ready_for_adversary", '
                '"selected_research_plan": {"plan_id": "p1", "summary": "s", "steps": []}}'
                "</MEDIATOR_OUTPUT>"
            )

        with mock.patch("agents.mediator_agent.single_llm_call", fake_single_llm_call):
            mediator = MediatorAgent(
                engine_name="main-engine",
                fast_engine_name="fast-engine",
                client=object(),
                result_dir=self.result_dir,
                max_schema_repair_attempts=1,
            )
            result = mediator.formulate(formulation_context={"foo": "bar"})

        self.assertEqual(result["formulation_status"], "ready_for_adversary")
        self.assertEqual(captured_models, ["main-engine", "fast-engine"])

    def test_json_repair_retry_falls_back_to_main_engine_when_fast_engine_not_wired(self):
        """If fast_engine_name is never passed in, the repair call must still use
        engine_name — confirming the default keeps behavior identical to before
        this change for any caller that hasn't wired a fast engine."""
        captured_models: list[str] = []

        def fake_single_llm_call(client, model, prompt, *, system=""):
            captured_models.append(model)
            if len(captured_models) == 1:
                return '<MEDIATOR_OUTPUT>{"formulation_status": "not_a_real_status"}</MEDIATOR_OUTPUT>'
            return (
                '<MEDIATOR_OUTPUT>{"formulation_status": "ready_for_adversary", '
                '"selected_research_plan": {"plan_id": "p1", "summary": "s", "steps": []}}'
                "</MEDIATOR_OUTPUT>"
            )

        with mock.patch("agents.mediator_agent.single_llm_call", fake_single_llm_call):
            mediator = MediatorAgent(
                engine_name="main-engine",
                client=object(),
                result_dir=self.result_dir,
                max_schema_repair_attempts=1,
            )
            mediator.formulate(formulation_context={"foo": "bar"})

        self.assertEqual(captured_models, ["main-engine", "main-engine"])


if __name__ == "__main__":
    unittest.main()
