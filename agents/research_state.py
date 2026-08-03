"""Task-scoped research state and context builders."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from agents.session_recorder import SessionRecorder
from agents.state_graph import StateGraphManager


@dataclass
class ResearchState:
    """Runtime source of truth for one research task.

    The state stores committed research information. Uncommitted candidate plans
    are passed explicitly into context builders.
    """

    user_question: str
    data_summary: dict[str, Any] | str
    recorder: SessionRecorder
    graph: StateGraphManager
    research_state_id: str = "S001"
    original_user_message: str = ""
    resolved_intent: str = ""
    session_context: dict[str, Any] = field(default_factory=dict)
    active_node_id: str | None = None
    evidence_state: dict[str, Any] = field(default_factory=dict)
    working_memory: dict[str, Any] = field(default_factory=lambda: {
        "panelist_outputs": {},
        "callback_history": [],
        "mediator_outputs": [],
        "adversary_outputs": [],
        "analyzer_reports": [],
        "tool_decisions": [],
    })
    selected_research_plan: dict[str, Any] = field(default_factory=dict)
    alternative_research_plans: list[dict[str, Any]] = field(default_factory=list)
    research_gap_resolution: list[Any] = field(default_factory=list)
    limitations: list[Any] = field(default_factory=list)

    def record_panelist_outputs(self, panelist_outputs: dict[str, Any]) -> None:
        self.working_memory["panelist_outputs"] = panelist_outputs

    def record_callback_history(self, callback_history: list[dict[str, Any]]) -> None:
        self.working_memory["callback_history"] = list(callback_history)

    def current_callback_history(self) -> list[dict[str, Any]]:
        return list(self.working_memory.get("callback_history", []))

    def record_adversary_output(self, adversary_output: dict[str, Any]) -> None:
        self.working_memory.setdefault("adversary_outputs", []).append(adversary_output)

    def record_mediator_output(self, mediator_output: dict[str, Any]) -> None:
        self.working_memory.setdefault("mediator_outputs", []).append(_compact_mediator_event(mediator_output))

    def record_tool_decision(self, tool_decision: dict[str, Any]) -> None:
        self.working_memory.setdefault("tool_decisions", []).append(_compact_tool_event(tool_decision))

    def record_analyzer_report(self, analyzer_report: dict[str, Any]) -> None:
        self.working_memory.setdefault("analyzer_reports", []).append(_compact_analyzer_event(analyzer_report))

    def update_evidence_state(self, evidence_state: dict[str, Any]) -> None:
        self.evidence_state = copy.deepcopy(evidence_state)
        node_id = self.active_node_id or self.graph.graph.get("active_node_id")
        if node_id:
            self.graph.update_evidence_state(str(node_id), evidence_state=self.evidence_state)

    def context_for_mediator_formulation(self) -> dict[str, Any]:
        return {
            "user_task": self.user_question,
            "original_user_message": self.original_user_message or self.user_question,
            "resolved_intent": self.resolved_intent or self.user_question,
            "data_summary": self.data_summary,
            "session_context": self.session_context,
            "active_plan": {
                "node_id": self.active_node_id,
                "selected_research_plan": self.selected_research_plan,
            },
            "panelist_outputs": self.working_memory.get("panelist_outputs", {}),
            "callback_history": self.working_memory.get("callback_history", []),
            "previous_mediator_outputs": self.working_memory.get("mediator_outputs", []),
            "previous_tool_decisions": self.working_memory.get("tool_decisions", []),
            "previous_analyzer_reports": self.working_memory.get("analyzer_reports", []),
            "evidence_state": self.evidence_state,
            "trajectory_summary": self.graph.trajectory_context(),
        }

    def context_for_mediator_adversary_revision(
        self,
        *,
        adversary_critique: dict[str, Any],
        adversary_revision_round: int,
        max_adversary_revision_rounds: int,
        candidate_plan: dict[str, Any] | None = None,
        candidate_trajectory_decision: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "user_task": self.user_question,
            "original_user_message": self.original_user_message or self.user_question,
            "resolved_intent": self.resolved_intent or self.user_question,
            "data_summary": self.data_summary,
            "session_context": self.session_context,
            "candidate_plan": candidate_plan or {},
            "candidate_trajectory_decision": candidate_trajectory_decision or {},
            "active_plan": {
                "node_id": self.active_node_id,
                "selected_research_plan": self.selected_research_plan,
                "limitations": self.limitations,
            },
            "evidence_state": self.evidence_state,
            "panelist_evidence_summary": self.working_memory.get("panelist_outputs", {}),
            "cited_papers": _collect_cited_papers(self.working_memory.get("panelist_outputs", {})),
            "adversary_critique": adversary_critique,
            "prior_mediator_outputs": self.working_memory.get("mediator_outputs", []),
            "prior_tool_decisions": self.working_memory.get("tool_decisions", []),
            "prior_analyzer_reports": self.working_memory.get("analyzer_reports", []),
            "callback_history": self.working_memory.get("callback_history", []),
            "adversary_revision_round": adversary_revision_round,
            "max_adversary_revision_rounds": max_adversary_revision_rounds,
            "trajectory_summary": self.graph.trajectory_context(),
            "alternative_research_plans": self.alternative_research_plans,
        }

    def context_for_mediator_post_analysis(
        self,
        *,
        phase_number: int,
        analyzer_report: dict[str, Any],
        dag_result_summary: dict[str, Any],
        tool_decision: dict[str, Any],
        artifact_registry_summary: dict[str, Any] | None = None,
        adversary_critique: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = {
            "user_task": self.user_question,
            "original_user_message": self.original_user_message or self.user_question,
            "resolved_intent": self.resolved_intent or self.user_question,
            "data_summary": self.data_summary,
            "session_context": self.session_context,
            "phase_number": phase_number,
            "active_plan": {
                "node_id": self.active_node_id,
                "selected_research_plan": self.selected_research_plan,
            },
            "evidence_state": self.evidence_state,
            "analyzer_report": analyzer_report,
            "dag_result_summary": dag_result_summary,
            "tool_decision": tool_decision,
            "artifact_registry_summary": artifact_registry_summary or {},
            "trajectory_summary": self.graph.trajectory_context(),
            "previous_mediator_outputs": self.working_memory.get("mediator_outputs", []),
            "previous_tool_decisions": self.working_memory.get("tool_decisions", []),
            "previous_analyzer_reports": self.working_memory.get("analyzer_reports", []),
            "callback_history": self.working_memory.get("callback_history", []),
            "unresolved_gaps": [],
            "research_gap_resolution": self.research_gap_resolution,
        }
        if adversary_critique:
            context["adversary_critique"] = adversary_critique
        return context

    def context_for_adversary(
        self,
        *,
        candidate_plan: dict[str, Any],
        candidate_trajectory_decision: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "user_question": self.user_question,
            "original_user_message": self.original_user_message or self.user_question,
            "resolved_intent": self.resolved_intent or self.user_question,
            "data_summary": self.data_summary,
            "candidate_plan": candidate_plan,
            "candidate_trajectory_decision": candidate_trajectory_decision,
            "evidence_state": self.evidence_state,
            "panelist_evidence_summary": self.working_memory.get("panelist_outputs", {}),
            "cited_papers": _collect_cited_papers(self.working_memory.get("panelist_outputs", {})),
            "research_gap_resolution": self.research_gap_resolution,
            "limitations": self.limitations,
            "prior_critiques": self.working_memory.get("adversary_outputs", []),
        }

    def context_for_tool_consultant(self, *, rerun_intent: dict[str, Any] | None = None) -> dict[str, Any]:
        context = self.graph.context_for_tool_consultant()
        context["user_question"] = self.user_question
        context["original_user_message"] = self.original_user_message or self.user_question
        context["resolved_intent"] = self.resolved_intent or self.user_question
        context["session_context"] = self.session_context
        context["selected_research_plan"] = self.selected_research_plan
        context["evidence_state"] = self.evidence_state
        if rerun_intent:
            context["rerun_intent"] = rerun_intent
        return context

    def commit_initial_plan(
        self,
        *,
        selected_plan: dict[str, Any],
        alternatives: list[dict[str, Any]] | None = None,
        trajectory_decision: dict[str, Any] | None = None,
        evidence_state: dict[str, Any] | None = None,
        plan_ref: str | None = None,
        plan_json_ref: str | None = None,
        trace_refs: dict[str, Any] | None = None,
    ) -> str:
        self.selected_research_plan = selected_plan
        self.alternative_research_plans = alternatives or []
        if evidence_state is not None:
            self.evidence_state = evidence_state
        node_id = self.graph.initialize_research_plan(
            selected_plan=selected_plan,
            alternatives=alternatives or [],
            user_question=self.user_question,
            plan_ref=plan_ref,
            plan_json_ref=plan_json_ref,
            evidence_state=self.evidence_state,
            trace_refs=trace_refs or {"trajectory_decision": trajectory_decision or {}},
        )
        self.active_node_id = node_id
        return node_id

    def mark_unanswerable(self, *, reason: str = "") -> str | None:
        node_id = self.active_node_id or self.graph.graph.get("active_node_id")
        if node_id:
            self.graph.set_node_status(str(node_id), status="unanswerable", active=False)
        self.active_node_id = None
        self.research_gap_resolution.append({"status": "unanswerable", "reason": reason})
        return str(node_id) if node_id else None


def _collect_cited_papers(panelist_outputs: Any) -> list[Any]:
    if not isinstance(panelist_outputs, dict):
        return []
    papers: list[Any] = []
    for value in panelist_outputs.values():
        if isinstance(value, dict):
            candidate = value.get("cited_papers") or value.get("literature_evidence")
            if isinstance(candidate, list):
                papers.extend(candidate)
    return papers


def _compact_mediator_event(event: dict[str, Any]) -> dict[str, Any]:
    output = event.get("output") if isinstance(event.get("output"), dict) else event
    selected_plan = output.get("selected_research_plan") if isinstance(output, dict) else {}
    if not isinstance(selected_plan, dict):
        selected_plan = output.get("updated_selected_research_plan") if isinstance(output, dict) else {}
    if not isinstance(selected_plan, dict):
        selected_plan = {}
    return {
        "source": event.get("source", ""),
        "phase_number": event.get("phase_number"),
        "trace_ref": event.get("trace_ref"),
        "status": output.get("formulation_status") or output.get("decision") or output.get("decision_type") or "",
        "plan_id": selected_plan.get("plan_id", ""),
        "plan_summary": selected_plan.get("summary", ""),
        "reason": output.get("rationale") or output.get("resolution_reason") or "",
        "research_gap_resolution": output.get("research_gap_resolution", []),
    }


def _compact_tool_event(event: dict[str, Any]) -> dict[str, Any]:
    decision = event.get("decision") if isinstance(event.get("decision"), dict) else event
    plan_kind = "research_brief"
    if isinstance(decision, dict) and decision.get("dag_plan"):
        plan_kind = "dag_plan"
    elif isinstance(decision, dict) and decision.get("implementation_plan"):
        plan_kind = "implementation_plan"
    return {
        "source": event.get("source", ""),
        "phase_number": event.get("phase_number"),
        "trace_ref": event.get("trace_ref"),
        "plan_kind": plan_kind,
        "task": decision.get("task", "") if isinstance(decision, dict) else "",
        "reason": decision.get("reason", "") if isinstance(decision, dict) else "",
        "execution_blocked": bool(decision.get("execution_blocked")) if isinstance(decision, dict) else False,
    }


def _compact_analyzer_event(event: dict[str, Any]) -> dict[str, Any]:
    report = event.get("report") if isinstance(event.get("report"), dict) else event
    return {
        "source": event.get("source", ""),
        "phase_number": event.get("phase_number"),
        "trace_ref": event.get("trace_ref"),
        "result_verdict": report.get("result_verdict", "") if isinstance(report, dict) else "",
        "results_summary": report.get("results_summary", "") if isinstance(report, dict) else "",
        "claim_updates": report.get("claim_updates", []) if isinstance(report, dict) else [],
    }
