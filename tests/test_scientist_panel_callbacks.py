from __future__ import annotations

import unittest

from agents.scientist_panel import ScientistPanel, _extract_callback_requests
from prompts.mediator_prompts import MEDIATOR_FORMULATION_PROMPT
from prompts.panelist_prompts import PANELIST_CALLBACK_PROMPT


class _CallbackPanel(ScientistPanel):
    def __init__(self, *, max_rounds=3):
        self.max_mediator_callback_rounds = max_rounds
        self.max_callbacks_per_round = 3
        self.max_callbacks_per_panelist_per_round = 1
        self.calls = []
        self.saves = []

    def _save(self, name, data):
        self.saves.append((name, data))

    def _run_panelist_callback(self, *, role, callback, context, round_number):
        self.calls.append(
            {
                "role": role,
                "callback": callback,
                "context": context,
                "round_number": round_number,
            }
        )
        return {
            "role": role,
            "assigned_gap": callback.get("assigned_gap", ""),
            "new_reasoning": f"{role} resolved gap",
            "gap_resolved": True,
        }


class _AcceptingCallbackPanel(_CallbackPanel):
    def _run_mediator_callback_synthesis(
        self,
        *,
        user_question,
        data_summary_str,
        prior_plan,
        callback_outputs,
        round_number,
        callback_history=None,
    ):
        plan = dict(prior_plan)
        plan["concrete_analysis_claim"] = "Revised claim after callback."
        plan["mediator_decision"] = "accept"
        plan["callbacks"] = []
        return plan


class _LoopingCallbackPanel(_CallbackPanel):
    def _run_mediator_callback_synthesis(
        self,
        *,
        user_question,
        data_summary_str,
        prior_plan,
        callback_outputs,
        round_number,
        callback_history=None,
    ):
        plan = dict(prior_plan)
        plan["mediator_decision"] = "needs_panelist_callback"
        plan["callbacks"] = [
            {
                "callback_type": "ask_panelist_for_more_reasoning",
                "callback_source": "mediator_gap",
                "role": "biologist",
                "assigned_gap": "Still missing biological definition.",
            }
        ]
        return plan


class _BriefCallbackPanel(_CallbackPanel):
    def _run_round1_formulate(self, *, user_question, data_summary_str, anchor_str):
        return {"biologist": "bio", "statistician": "stat", "bioinformatician": "comp"}

    def _run_mediator_formulation(self, *, user_question, data_summary_str, panelist_outputs):
        return {
            "selected_research_plan": {"steps": []},
            "mediator_decision": "needs_panelist_callback",
            "callbacks": [
                {
                    "callback_type": "ask_panelist_for_more_reasoning",
                    "callback_source": "mediator_gap",
                    "role": "biologist",
                    "assigned_gap": "Need biological definition.",
                }
            ],
        }


class ScientistPanelCallbackTests(unittest.TestCase):
    def test_callback_prompts_define_required_tags(self):
        self.assertIn("<CALLBACK_OUTPUT>", PANELIST_CALLBACK_PROMPT)
        self.assertIn("<MEDIATOR_OUTPUT>", MEDIATOR_FORMULATION_PROMPT)

    def test_extract_callback_requests_limits_roles_and_counts(self):
        callbacks = _extract_callback_requests(
            {
                "callbacks": [
                    {"role": "biologist", "callback_type": "ask_panelist_for_more_reasoning", "assigned_gap": "A"},
                    {"role": "biologist", "callback_type": "ask_panelist_for_more_literature", "assigned_gap": "B"},
                    {"role": "statistician", "callback_type": "ask_panelist_for_more_reasoning", "assigned_gap": "C"},
                    {"role": "invalid", "callback_type": "ask_panelist_for_more_reasoning", "assigned_gap": "D"},
                ]
            },
            max_callbacks=3,
            max_per_role=1,
        )

        self.assertEqual([c["role"] for c in callbacks], ["biologist", "statistician"])
        self.assertEqual([c["assigned_gap"] for c in callbacks], ["A", "C"])

    def test_invalid_callbacks_are_tracked_by_normalizer(self):
        from agents.scientist_panel import _normalize_research_plan_schema

        normalized = _normalize_research_plan_schema(
            {
                "selected_research_plan": {"steps": []},
                "callbacks": [
                    {"role": "statistician", "callback_type": "ask_panelist_for_more_reasoning", "assigned_gap": "Need unit."},
                    {"role": "invalid", "callback_type": "ask_panelist_for_more_reasoning", "assigned_gap": "Bad role."},
                    {"role": "biologist", "callback_type": "bad", "assigned_gap": "Bad type."},
                    {"role": "biologist", "callback_type": "ask_panelist_for_more_reasoning", "assigned_gap": ""},
                ],
            }
        )

        self.assertEqual(len(normalized["callbacks"]), 1)
        self.assertEqual(normalized["callbacks"][0]["role"], "statistician")
        self.assertEqual(len(normalized["_invalid_callbacks"]), 3)

    def test_mediator_callback_runs_only_assigned_panelist(self):
        panel = _AcceptingCallbackPanel()
        result = panel._run_mediator_callback_loop(
            user_question="Question",
            data_summary_str="Data",
            panelist_outputs={"biologist": "bio", "statistician": "stat", "bioinformatician": "comp"},
            current_plan={
                "concrete_analysis_claim": "Initial claim.",
                "selected_research_plan": {"steps": []},
                "callbacks": [
                    {
                        "callback_type": "ask_panelist_for_more_reasoning",
                        "callback_source": "mediator_gap",
                        "role": "statistician",
                        "assigned_gap": "Need statistical unit.",
                    }
                ],
            },
        )

        self.assertEqual([call["role"] for call in panel.calls], ["statistician"])
        self.assertEqual(result["concrete_analysis_claim"], "Revised claim after callback.")
        self.assertFalse(result["_callback_budget_exhausted"])

    def test_callback_context_excludes_execution_state(self):
        panel = _AcceptingCallbackPanel()
        panel._last_adversarial_result = {
            "verdict": "needs_revision",
            "last_challenge": {
                "summary": "Plan needs donor-level evidence.",
                "recommended_revision": "Add sample-level abundance testing.",
                "challenges": [{"target": "abundance step"}],
            },
        }
        context = panel._build_panelist_callback_context(
            user_question="Question",
            data_summary_str="Data",
            panelist_outputs={"biologist": "bio", "statistician": "stat", "bioinformatician": "comp"},
            current_plan={
                "selected_research_plan": {"steps": []},
                "alternative_research_plans": [],
                "analysis_requirements": ["Use donor-level inference."],
                "open_risks": ["No donor column."],
            },
            callback={
                "role": "biologist",
                "callback_type": "ask_panelist_for_more_reasoning",
                "callback_source": "mediator_gap",
                "assigned_gap": "Clarify marker definition.",
            },
            callback_history=[],
        )

        text = str(context).lower()
        self.assertIn("panelist_state", context)
        self.assertIn("mediated_state", context)
        self.assertEqual(context["adversarial_state"]["critique_summary"], "Plan needs donor-level evidence.")
        self.assertEqual(context["adversarial_state"]["critique_target"], "abundance step")
        self.assertEqual(context["adversarial_state"]["required_revision"], "Add sample-level abundance testing.")
        self.assertNotIn("tool plan", text)
        self.assertNotIn("implementation plan", text)
        self.assertNotIn("dependency", text)
        self.assertNotIn("artifact path", text)

    def test_post_analysis_callbacks_preserve_research_context(self):
        panel = _AcceptingCallbackPanel(max_rounds=1)
        panel.max_callback_rounds_after_analysis = 1
        result = panel.run_post_analysis_callbacks(
            user_question="Question",
            data_summary={"n_cells": 10},
            phase_number=1,
            post_analysis_decision={
                "decision": "call_panelists",
                "callbacks": [
                    {
                        "role": "biologist",
                        "callback_type": "ask_panelist_for_more_reasoning",
                        "assigned_gap": "Clarify biological claim.",
                    }
                ],
            },
            working_model={},
            research_context={
                "concrete_analysis_claim": "T cells expand in disease.",
                "research_case": "extension",
                "selected_research_plan": {"summary": "Existing solution plus extension.", "steps": []},
                "evidence_patterns": [{"statistical_unit": "sample"}],
            },
        )

        self.assertEqual(result["concrete_analysis_claim"], "Revised claim after callback.")
        self.assertEqual(panel.calls[0]["context"]["mediated_state"]["concrete_analysis_claim"], "T cells expand in disease.")
        self.assertEqual(panel.calls[0]["context"]["mediated_state"]["selected_research_plan"]["summary"], "Existing solution plus extension.")
        self.assertEqual(panel.calls[0]["context"]["original_task"]["user_question"], "Question")

    def test_callback_round_limit_prevents_infinite_loop(self):
        panel = _LoopingCallbackPanel(max_rounds=1)
        result = panel._run_mediator_callback_loop(
            user_question="Question",
            data_summary_str="Data",
            panelist_outputs={"biologist": "bio", "statistician": "stat", "bioinformatician": "comp"},
            current_plan={
                "concrete_analysis_claim": "Initial claim.",
                "selected_research_plan": {"steps": []},
                "callbacks": [
                    {
                        "callback_type": "ask_panelist_for_more_reasoning",
                        "callback_source": "mediator_gap",
                        "role": "biologist",
                        "assigned_gap": "Need biological definition.",
                    }
                ],
            },
        )

        self.assertEqual(result["_callback_rounds"], 1)
        self.assertTrue(result["_callback_budget_exhausted"])
        self.assertEqual(len(panel.calls), 1)

    def test_formulate_brief_flags_skipped_callbacks(self):
        panel = _BriefCallbackPanel()
        result = panel._formulate_brief(
            user_question="Question",
            data_summary={"n_cells": 10},
            anchor_papers=[],
        )

        self.assertTrue(result["_callbacks_skipped"])
        self.assertTrue(result["_callback_budget_exhausted"])
        self.assertEqual(result["_callback_skip_reason"], "brief mode does not run mediator callbacks")
        self.assertEqual(result["_skipped_callbacks"][0]["role"], "biologist")

    def test_callback_history_passed_to_mediator_synthesis(self):
        class _HistoryPanel(_CallbackPanel):
            def __init__(self):
                super().__init__(max_rounds=2)
                self.history_lengths = []

            def _run_mediator_callback_synthesis(
                self,
                *,
                user_question,
                data_summary_str,
                prior_plan,
                callback_outputs,
                round_number,
                callback_history=None,
            ):
                self.history_lengths.append(len(callback_history or []))
                return {
                    "selected_research_plan": {"steps": []},
                    "mediator_decision": "needs_panelist_callback" if round_number == 1 else "accept",
                    "callbacks": [
                        {
                            "callback_type": "ask_panelist_for_more_reasoning",
                            "callback_source": "mediator_gap",
                            "role": "statistician",
                            "assigned_gap": "Need statistical unit.",
                        }
                    ] if round_number == 1 else [],
                }

        panel = _HistoryPanel()
        panel._run_mediator_callback_loop(
            user_question="Question",
            data_summary_str="Data",
            panelist_outputs={"biologist": "bio", "statistician": "stat", "bioinformatician": "comp"},
            current_plan={
                "selected_research_plan": {"steps": []},
                "callbacks": [
                    {
                        "callback_type": "ask_panelist_for_more_reasoning",
                        "callback_source": "mediator_gap",
                        "role": "biologist",
                        "assigned_gap": "Need biological definition.",
                    }
                ],
            },
        )

        self.assertEqual(panel.history_lengths, [1, 2])


if __name__ == "__main__":
    unittest.main()
