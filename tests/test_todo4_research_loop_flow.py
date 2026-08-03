from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.adversarial_panelist import _validate_challenge_output
from agents.decision_schema import DecisionValidationError
from agents.mediator_agent import MediatorAgent
from agents.research_loop import ResearchLoop, _resolve_candidate_revision


class _Scientist:
    max_mediator_callback_rounds = 1
    max_callbacks_per_round = 2

    def run_initial_panelists(self, **_):
        return {
            "biologist": "bio evidence",
            "statistician": "stat evidence",
            "bioinformatician": "comp evidence",
        }

    def run_panelist_callback(self, role, callback_input):
        return {"role": role, "gap_resolved": True, "callback_input": callback_input}


class _ToolConsultant:
    def decide(self, **_):
        return {"implementation_plan": {"steps": ["write result"]}}


class _Coder:
    def run(self, **_):
        return {"status": "completed", "outputs": {"table": "dummy.csv"}}


class _Analyzer:
    def analyze(self, **_):
        return {"result_verdict": "supported", "results_summary": "dummy analyzed", "claim_updates": []}


def test_adversary_invalid_verdict_is_schema_error():
    with pytest.raises(DecisionValidationError):
        _validate_challenge_output({"verdict": "accepted", "summary": "bad schema"})


def test_research_loop_passes_candidate_plan_to_adversary(tmp_path: Path):
    input_path = tmp_path / "input.csv"
    input_path.write_text("cell,gene\na,b\n", encoding="utf-8")

    class Mediator:
        def __init__(self):
            self.formulation_contexts = []
            self.post_contexts = []

        def formulate(self, *, formulation_context):
            self.formulation_contexts.append(formulation_context)
            return {
                "formulation_status": "ready_for_adversary",
                "selected_research_plan": {"plan_id": "p1", "summary": "dummy", "steps": ["qc", "cluster"]},
                "trajectory_decision": {"action": "initialize_plan", "branch_from_node_id": None, "reason": "test"},
                "evidence_state": {"analysis_claims": []},
            }

        def synthesize_callbacks(self, **_):
            raise AssertionError("not expected")

        def revise_from_adversary(self, **_):
            raise AssertionError("not expected")

        def post_analysis(self, *, post_analysis_context):
            self.post_contexts.append(post_analysis_context)
            return {"decision": "accept_and_conclude", "decision_type": "accept_and_conclude"}

    class Adversary:
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

    mediator = Mediator()
    adversary = Adversary()
    loop = ResearchLoop(
        scientist_panel=_Scientist(),
        analyzer_panel=_Analyzer(),
        tool_consultant=_ToolConsultant(),
        coder=_Coder(),
        input_h5ad_path=str(input_path),
        data_summary={"modality": "dummy"},
        result_dir=tmp_path / "results",
        max_phases=1,
        mediator_agent=mediator,
        adversarial_panelist=adversary,
    )

    result = loop.run(user_question="dummy question")

    assert result["status"] == "done"
    phase0 = (tmp_path / "results" / "phase0_formulate.json").read_text(encoding="utf-8")
    assert "adversary_survives" in phase0
    assert '"adversarial_review_status": "survives"' in phase0
    assert '"adversarial_review_interpretation": "reviewed_no_blocking_flaw"' in phase0
    assert mediator.formulation_contexts[0]["panelist_outputs"]["biologist"] == "bio evidence"
    assert adversary.contexts[0]["candidate_plan"]["plan_id"] == "p1"
    assert adversary.contexts[0]["candidate_trajectory_decision"]["action"] == "initialize_plan"
    assert adversary.contexts[0]["data_summary"]["modality"] == "dummy"
    assert "analyzer_report" in mediator.post_contexts[0]
    assert mediator.post_contexts[0]["previous_mediator_outputs"][0]["source"] == "formulation"
    assert mediator.post_contexts[0]["previous_tool_decisions"]
    assert mediator.post_contexts[0]["previous_analyzer_reports"][0]["result_verdict"] == "supported"


def test_formulation_skipped_adversary_is_not_reported_as_reviewed(tmp_path: Path):
    input_path = tmp_path / "input.csv"
    input_path.write_text("cell,gene\na,b\n", encoding="utf-8")

    class Mediator:
        def formulate(self, *, formulation_context):
            return {
                "formulation_status": "ready_for_adversary",
                "selected_research_plan": {"plan_id": "p1", "steps": ["a"]},
                "trajectory_decision": {"action": "initialize_plan", "branch_from_node_id": None, "reason": "init"},
            }

        def synthesize_callbacks(self, **_):
            raise AssertionError("not expected")

        def revise_from_adversary(self, **_):
            raise AssertionError("skipped adversary review should not request revision")

        def post_analysis(self, *, post_analysis_context):
            return {"decision": "accept_and_conclude", "decision_type": "accept_and_conclude"}

    class Adversary:
        max_rounds = 1

        def run(self, *, adversary_context):
            return {"adversary_verdict": "skipped", "verdict": "skipped"}

    loop = ResearchLoop(
        scientist_panel=_Scientist(),
        analyzer_panel=_Analyzer(),
        tool_consultant=_ToolConsultant(),
        coder=_Coder(),
        input_h5ad_path=str(input_path),
        data_summary={"modality": "dummy"},
        result_dir=tmp_path / "results",
        max_phases=1,
        mediator_agent=Mediator(),
        adversarial_panelist=Adversary(),
    )

    result = loop.run(user_question="dummy question")

    assert result["status"] == "done"
    phase0 = (tmp_path / "results" / "phase0_formulate.json").read_text(encoding="utf-8")
    assert '"resolution_reason": "adversary_skipped"' in phase0
    assert '"adversarial_review_status": "skipped"' in phase0
    assert '"adversarial_review_interpretation": "not_reviewed"' in phase0


def test_callback_synthesis_context_uses_prior_history_only(tmp_path: Path):
    input_path = tmp_path / "input.csv"
    input_path.write_text("cell,gene\na,b\n", encoding="utf-8")

    class Mediator:
        def __init__(self):
            self.synthesis_contexts = []
            self.synthesis_outputs = []

        def formulate(self, *, formulation_context):
            return {
                "formulation_status": "needs_panelist_callback",
                "callback_requests": [{"role": "biologist", "assigned_gap": "gap 1"}],
            }

        def synthesize_callbacks(self, *, formulation_context, callback_outputs, round_number):
            self.synthesis_contexts.append(formulation_context)
            self.synthesis_outputs.append(callback_outputs)
            return {
                "formulation_status": "ready_for_adversary",
                "selected_research_plan": {"plan_id": "p1", "steps": ["a"]},
                "trajectory_decision": {"action": "initialize_plan", "branch_from_node_id": None, "reason": "ready"},
            }

        def revise_from_adversary(self, **_):
            raise AssertionError("not expected")

        def post_analysis(self, *, post_analysis_context):
            return {"decision": "accept_and_conclude", "decision_type": "accept_and_conclude"}

    class Adversary:
        max_rounds = 1

        def run(self, *, adversary_context):
            return {"adversary_verdict": "survives", "verdict": "survives"}

    mediator = Mediator()
    loop = ResearchLoop(
        scientist_panel=_Scientist(),
        analyzer_panel=_Analyzer(),
        tool_consultant=_ToolConsultant(),
        coder=_Coder(),
        input_h5ad_path=str(input_path),
        data_summary={"modality": "dummy"},
        result_dir=tmp_path / "results",
        max_phases=1,
        mediator_agent=mediator,
        adversarial_panelist=Adversary(),
    )

    result = loop.run(user_question="dummy question")

    assert result["status"] == "done"
    assert mediator.synthesis_contexts[0]["callback_history"] == []
    assert mediator.synthesis_outputs[0][0]["callback"]["assigned_gap"] == "gap 1"


def test_post_analysis_skipped_is_not_reviewed_and_does_not_revise(tmp_path: Path):
    input_path = tmp_path / "input.csv"
    input_path.write_text("cell,gene\na,b\n", encoding="utf-8")

    class Mediator:
        def formulate(self, *, formulation_context):
            return {
                "formulation_status": "ready_for_adversary",
                "selected_research_plan": {"plan_id": "p1", "steps": ["a"]},
                "trajectory_decision": {"action": "initialize_plan", "branch_from_node_id": None, "reason": "init"},
            }

        def synthesize_callbacks(self, **_):
            raise AssertionError("not expected")

        def revise_from_adversary(self, **_):
            raise AssertionError("skipped adversary review should not request revision")

        def post_analysis(self, *, post_analysis_context):
            return {
                "decision": "self_revise_plan",
                "decision_type": "self_revise_plan",
                "updated_selected_research_plan": {"plan_id": "p2", "steps": ["b"]},
                "trajectory_decision": {
                    "action": "create_revised_node",
                    "branch_from_node_id": "plan_001",
                    "reason": "revise",
                },
            }

    class Adversary:
        max_rounds = 1

        def run(self, *, adversary_context):
            if adversary_context["candidate_plan"].get("plan_id") == "p1":
                return {"adversary_verdict": "survives", "verdict": "survives"}
            return {"adversary_verdict": "skipped", "verdict": "skipped"}

    loop = ResearchLoop(
        scientist_panel=_Scientist(),
        analyzer_panel=_Analyzer(),
        tool_consultant=_ToolConsultant(),
        coder=_Coder(),
        input_h5ad_path=str(input_path),
        data_summary={"modality": "dummy"},
        result_dir=tmp_path / "results",
        max_phases=2,
        mediator_agent=Mediator(),
        adversarial_panelist=Adversary(),
    )

    result = loop.run(user_question="dummy question")

    assert result["phase_log"][0]["post_analysis_decision"] == "self_revise_plan"
    decision_path = tmp_path / "results" / "phase1_post_analysis_decision.json"
    decision_text = decision_path.read_text(encoding="utf-8")
    assert '"adversarial_review_status": "skipped"' in decision_text
    assert '"adversarial_review_interpretation": "not_reviewed"' in decision_text


def test_post_analysis_evidence_state_carries_to_next_phase_contexts(tmp_path: Path):
    input_path = tmp_path / "input.csv"
    input_path.write_text("cell,gene\na,b\n", encoding="utf-8")

    phase1_evidence = {
        "analysis_claims": [
            {
                "claim_id": "C1",
                "claim_text": "dummy claim",
                "status": "partially_supported",
                "support_summary": "phase 1 evidence",
                "contradicting_evidence": [],
                "unresolved_requirements": ["one more metric"],
            }
        ],
        "current_belief": "phase 1 updated belief",
    }
    phase2_evidence = {
        "analysis_claims": [
            {
                "claim_id": "C1",
                "claim_text": "dummy claim",
                "status": "supported",
                "support_summary": "phase 2 evidence",
                "contradicting_evidence": [],
                "unresolved_requirements": [],
            }
        ],
        "current_belief": "phase 2 final belief",
    }

    class Mediator:
        def __init__(self):
            self.post_contexts = []

        def formulate(self, *, formulation_context):
            return {
                "formulation_status": "ready_for_adversary",
                "selected_research_plan": {"plan_id": "p1", "steps": ["a"]},
                "trajectory_decision": {"action": "initialize_plan", "branch_from_node_id": None, "reason": "init"},
                "evidence_state": {"analysis_claims": [], "current_belief": "initial"},
            }

        def synthesize_callbacks(self, **_):
            raise AssertionError("not expected")

        def revise_from_adversary(self, **_):
            raise AssertionError("not expected")

        def post_analysis(self, *, post_analysis_context):
            self.post_contexts.append(post_analysis_context)
            if len(self.post_contexts) == 1:
                return {
                    "decision": "continue_with_same_research_plan",
                    "decision_type": "continue_with_same_research_plan",
                    "updated_selected_research_plan": {"plan_id": "p1", "steps": ["a"]},
                    "evidence_state": phase1_evidence,
                    "rerun_intent": {"reason": "need one more metric"},
                }
            return {
                "decision": "accept_and_conclude",
                "decision_type": "accept_and_conclude",
                "updated_selected_research_plan": {"plan_id": "p1", "steps": ["a"]},
                "evidence_state": phase2_evidence,
            }

    class ToolConsultant:
        def __init__(self):
            self.session_states = []

        def decide(self, *, user_message, session_state, session_tag):
            self.session_states.append(session_state)
            return {"implementation_plan": {"steps": ["write result"]}}

    class Adversary:
        max_rounds = 1

        def run(self, *, adversary_context):
            return {"adversary_verdict": "survives", "verdict": "survives"}

    mediator = Mediator()
    tool_consultant = ToolConsultant()
    loop = ResearchLoop(
        scientist_panel=_Scientist(),
        analyzer_panel=_Analyzer(),
        tool_consultant=tool_consultant,
        coder=_Coder(),
        input_h5ad_path=str(input_path),
        data_summary={"modality": "dummy"},
        result_dir=tmp_path / "results",
        max_phases=2,
        mediator_agent=mediator,
        adversarial_panelist=Adversary(),
    )

    result = loop.run(user_question="dummy question")

    assert result["status"] == "done"
    assert mediator.post_contexts[1]["evidence_state"] == phase1_evidence
    assert tool_consultant.session_states[1]["evidence_state"] == phase1_evidence

    graph = json.loads((tmp_path / "results" / "runs" / "conversations" / "C001" / "sessions" / "S001" / "state_graph.json").read_text(encoding="utf-8"))
    assert graph["nodes"]["plan_001"]["evidence_state"] == phase2_evidence


def test_post_analysis_unsalvageable_routes_back_to_post_analysis(tmp_path: Path):
    input_path = tmp_path / "input.csv"
    input_path.write_text("cell,gene\na,b\n", encoding="utf-8")

    class Mediator:
        def __init__(self):
            self.post_contexts = []

        def formulate(self, *, formulation_context):
            return {
                "formulation_status": "ready_for_adversary",
                "selected_research_plan": {"plan_id": "p1", "steps": ["a"]},
                "trajectory_decision": {"action": "initialize_plan", "branch_from_node_id": None, "reason": "init"},
            }

        def synthesize_callbacks(self, **_):
            raise AssertionError("not expected")

        def revise_from_adversary(self, **_):
            raise AssertionError("post-analysis unsalvageable should not call revise_from_adversary")

        def post_analysis(self, *, post_analysis_context):
            self.post_contexts.append(post_analysis_context)
            if len(self.post_contexts) == 1:
                return {
                    "decision": "self_revise_plan",
                    "decision_type": "self_revise_plan",
                    "updated_selected_research_plan": {"plan_id": "p2", "steps": ["b"]},
                    "trajectory_decision": {
                        "action": "create_revised_node",
                        "branch_from_node_id": "plan_001",
                        "reason": "revise",
                    },
                }
            return {"decision": "ask_user", "decision_type": "ask_user", "clarifying_questions": ["Need input"]}

    class Adversary:
        max_rounds = 1

        def __init__(self):
            self.calls = 0

        def run(self, *, adversary_context):
            self.calls += 1
            if adversary_context["candidate_plan"].get("plan_id") == "p1":
                return {"adversary_verdict": "survives", "verdict": "survives"}
            return {"adversary_verdict": "unsalvageable", "verdict": "unsalvageable", "critique_summary": "bad"}

    mediator = Mediator()
    loop = ResearchLoop(
        scientist_panel=_Scientist(),
        analyzer_panel=_Analyzer(),
        tool_consultant=_ToolConsultant(),
        coder=_Coder(),
        input_h5ad_path=str(input_path),
        data_summary={"modality": "dummy"},
        result_dir=tmp_path / "results",
        max_phases=1,
        mediator_agent=mediator,
        adversarial_panelist=Adversary(),
    )

    result = loop.run(user_question="dummy question")

    assert result["status"] == "awaiting_user"
    assert "adversary_critique" in mediator.post_contexts[-1]


class _FakeResponse:
    def __init__(self, text: str):
        self.output_text = text


class _FakeResponses:
    def __init__(self, outputs):
        self.outputs = list(outputs)

    def create(self, **_):
        if not self.outputs:
            raise AssertionError("No fake LLM outputs remaining")
        return _FakeResponse(self.outputs.pop(0))


class _FakeClient:
    def __init__(self, outputs):
        self.responses = _FakeResponses(outputs)


def test_mediator_post_analysis_repairs_invalid_schema(tmp_path: Path):
    client = _FakeClient(
        [
            '<MEDIATOR_POST_ANALYSIS>{"decision": "bad_old_alias"}</MEDIATOR_POST_ANALYSIS>',
            '<MEDIATOR_POST_ANALYSIS>{"decision": "accept_and_conclude", "rationale": "fixed"}</MEDIATOR_POST_ANALYSIS>',
        ]
    )
    mediator = MediatorAgent(engine_name="fake", client=client, result_dir=tmp_path)

    result = mediator.post_analysis(post_analysis_context={"phase_number": 1})

    assert result["decision"] == "accept_and_conclude"
    assert result["rationale"] == "fixed"


def test_mediator_post_analysis_internal_panelist_callback_loop(tmp_path: Path):
    client = _FakeClient(
        [
            """
            <MEDIATOR_POST_ANALYSIS>
            {"decision": "needs_panelist_callback", "callback_requests": [{"role": "biologist", "question": "check biology"}]}
            </MEDIATOR_POST_ANALYSIS>
            """,
            '<MEDIATOR_POST_ANALYSIS>{"decision": "accept_and_conclude", "rationale": "callback resolved"}</MEDIATOR_POST_ANALYSIS>',
        ]
    )
    callback_calls = []

    def callback_executor(role, callback_input):
        callback_calls.append((role, callback_input))
        return {"answer": "biologically plausible"}

    mediator = MediatorAgent(
        engine_name="fake",
        client=client,
        result_dir=tmp_path,
        panelist_callback_executor=callback_executor,
    )

    result = mediator.post_analysis(post_analysis_context={"phase_number": 1})

    assert result["decision"] == "accept_and_conclude"
    assert callback_calls[0][0] == "biologist"
    assert result["panelist_callback_findings"][0]["finding"]["answer"] == "biologically plausible"


def test_last_round_adversary_revision_can_declare_unanswerable(tmp_path: Path):
    input_path = tmp_path / "input.csv"
    input_path.write_text("cell,gene\na,b\n", encoding="utf-8")

    class Mediator:
        def formulate(self, *, formulation_context):
            return {
                "formulation_status": "ready_for_adversary",
                "selected_research_plan": {"plan_id": "p1", "steps": ["a"]},
                "trajectory_decision": {"action": "initialize_plan", "branch_from_node_id": None, "reason": "init"},
            }

        def synthesize_callbacks(self, **_):
            raise AssertionError("not expected")

        def revise_from_adversary(self, **_):
            return {
                "formulation_status": "ready_for_adversary",
                "selected_research_plan": {"plan_id": "p1", "steps": ["a"]},
                "trajectory_decision": {
                    "action": "declare_unanswerable",
                    "branch_from_node_id": None,
                    "reason": "No defensible plan exists.",
                },
            }

        def post_analysis(self, **_):
            raise AssertionError("execution should not start")

    class Adversary:
        max_rounds = 1

        def run(self, *, adversary_context):
            return {"adversary_verdict": "needs_revision", "verdict": "needs_revision"}

    loop = ResearchLoop(
        scientist_panel=_Scientist(),
        analyzer_panel=_Analyzer(),
        tool_consultant=_ToolConsultant(),
        coder=_Coder(),
        input_h5ad_path=str(input_path),
        data_summary={"modality": "dummy"},
        result_dir=tmp_path / "results",
        max_phases=1,
        mediator_agent=Mediator(),
        adversarial_panelist=Adversary(),
    )

    result = loop.run(user_question="dummy question")

    assert result["status"] == "abstain"
    assert result["phases_completed"] == 0


def test_unsalvageable_requires_material_revision_or_stops(tmp_path: Path):
    input_path = tmp_path / "input.csv"
    input_path.write_text("cell,gene\na,b\n", encoding="utf-8")

    class Mediator:
        def formulate(self, *, formulation_context):
            return {
                "formulation_status": "ready_for_adversary",
                "selected_research_plan": {"plan_id": "p1", "summary": "same", "steps": ["a"]},
                "trajectory_decision": {"action": "initialize_plan", "branch_from_node_id": None, "reason": "init"},
            }

        def synthesize_callbacks(self, **_):
            raise AssertionError("not expected")

        def revise_from_adversary(self, **_):
            return {
                "formulation_status": "ready_for_adversary",
                "selected_research_plan": {"plan_id": "p1", "summary": "same", "steps": ["a"]},
                "trajectory_decision": {"action": "initialize_plan", "branch_from_node_id": None, "reason": "cosmetic"},
            }

        def post_analysis(self, **_):
            raise AssertionError("execution should not start")

    class Adversary:
        max_rounds = 1

        def run(self, *, adversary_context):
            return {"adversary_verdict": "unsalvageable", "verdict": "unsalvageable"}

    loop = ResearchLoop(
        scientist_panel=_Scientist(),
        analyzer_panel=_Analyzer(),
        tool_consultant=_ToolConsultant(),
        coder=_Coder(),
        input_h5ad_path=str(input_path),
        data_summary={"modality": "dummy"},
        result_dir=tmp_path / "results",
        max_phases=1,
        mediator_agent=Mediator(),
        adversarial_panelist=Adversary(),
    )

    result = loop.run(user_question="dummy question")

    assert result["status"] == "abstain"
    assert result["phases_completed"] == 0


def test_nonterminal_unsalvageable_resolution_keeps_prior_trajectory():
    previous_plan = {"plan_id": "p1", "summary": "same", "steps": ["a"]}
    previous_trajectory = {"action": "initialize_plan", "reason": "prior"}

    resolution = _resolve_candidate_revision(
        previous_plan=previous_plan,
        previous_trajectory=previous_trajectory,
        revised_output={
            "selected_research_plan": {"plan_id": "p1", "summary": "same", "steps": ["a"]},
            "trajectory_decision": {"action": "initialize_plan", "reason": "cosmetic"},
        },
        adversary_verdict="unsalvageable",
        force_terminal=False,
    )

    assert resolution["status"] == "needs_revision"
    assert resolution["trajectory_decision"] == previous_trajectory
    assert resolution["reason"] == "unsalvageable_without_material_revision"


def test_terminal_unsalvageable_resolution_declares_unanswerable():
    previous_plan = {"plan_id": "p1", "summary": "same", "steps": ["a"]}

    resolution = _resolve_candidate_revision(
        previous_plan=previous_plan,
        previous_trajectory={"action": "initialize_plan", "reason": "prior"},
        revised_output={
            "selected_research_plan": {"plan_id": "p1", "summary": "same", "steps": ["a"]},
            "trajectory_decision": {"action": "initialize_plan", "reason": "cosmetic"},
        },
        adversary_verdict="unsalvageable",
        force_terminal=True,
    )

    assert resolution["status"] == "unanswerable"
    assert resolution["trajectory_decision"]["action"] == "declare_unanswerable"


def test_post_analysis_unsalvageable_budget_exhaustion_declares_unanswerable(tmp_path: Path):
    input_path = tmp_path / "input.csv"
    input_path.write_text("cell,gene\na,b\n", encoding="utf-8")

    class Mediator:
        def formulate(self, *, formulation_context):
            return {
                "formulation_status": "ready_for_adversary",
                "selected_research_plan": {"plan_id": "p1", "steps": ["a"]},
                "trajectory_decision": {"action": "initialize_plan", "branch_from_node_id": None, "reason": "init"},
            }

        def synthesize_callbacks(self, **_):
            raise AssertionError("not expected")

        def revise_from_adversary(self, **_):
            raise AssertionError("post-analysis unsalvageable should use post_analysis")

        def post_analysis(self, *, post_analysis_context):
            return {
                "decision": "self_revise_plan",
                "decision_type": "self_revise_plan",
                "updated_selected_research_plan": {"plan_id": "p2", "steps": ["b"]},
                "trajectory_decision": {
                    "action": "create_revised_node",
                    "branch_from_node_id": "plan_001",
                    "reason": "try another revision",
                },
            }

    class Adversary:
        max_rounds = 1

        def run(self, *, adversary_context):
            if adversary_context["candidate_plan"].get("plan_id") == "p1":
                return {"adversary_verdict": "survives", "verdict": "survives"}
            return {"adversary_verdict": "unsalvageable", "verdict": "unsalvageable"}

    loop = ResearchLoop(
        scientist_panel=_Scientist(),
        analyzer_panel=_Analyzer(),
        tool_consultant=_ToolConsultant(),
        coder=_Coder(),
        input_h5ad_path=str(input_path),
        data_summary={"modality": "dummy"},
        result_dir=tmp_path / "results",
        max_phases=1,
        mediator_agent=Mediator(),
        adversarial_panelist=Adversary(),
    )

    result = loop.run(user_question="dummy question")

    assert result["status"] == "abstain"
    assert result["post_analysis_decision"]["resolution_reason"] == "adversary_budget_exhausted_without_defensible_revision"
