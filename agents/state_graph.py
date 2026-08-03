from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class StateGraphError(ValueError):
    pass


class StateGraphManager:
    """Deterministic helper for Phase 6 solution/plan state graphs."""

    def __init__(self, *, session_dir: str | Path):
        self.session_dir = Path(session_dir)
        self.path = self.session_dir / "state_graph.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(_empty_graph())

    @property
    def graph(self) -> dict[str, Any]:
        return self._read()

    def initialize_research_plan(
        self,
        *,
        selected_plan: dict[str, Any],
        alternatives: list[dict[str, Any]] | None = None,
        user_question: str,
        plan_ref: str | None = None,
        plan_json_ref: str | None = None,
        evidence_state: dict[str, Any] | None = None,
        trace_refs: dict[str, Any] | None = None,
    ) -> str:
        graph = self._read()
        if graph.get("active_node_id"):
            active = graph.get("nodes", {}).get(graph["active_node_id"], {})
            if isinstance(active, dict) and _materially_different_plan(active, selected_plan):
                graph.setdefault("warnings", []).append(
                    {
                        "created_at": _now(),
                        "warning": "initialize_research_plan called with a different selected_plan while an active node already exists.",
                        "active_node_id": graph["active_node_id"],
                        "incoming_plan_summary": _plan_summary(selected_plan),
                    }
                )
                self._write(graph)
            return str(graph["active_node_id"])
        node_id = self._next_node_id(graph, "plan")
        node = _base_node(
            node_id=node_id,
            node_type="research_plan",
            mode="discovery",
            status="active",
            summary=_plan_summary(selected_plan) or user_question,
        )
        node.update(
            {
                "plan_id": selected_plan.get("plan_id") or "plan_a",
                "role": "selected",
                "parent_node_id": None,
                "user_question": user_question,
                "plan_path": plan_ref,
                "plan_json_path": plan_json_ref,
                "steps": selected_plan.get("steps", []),
                "evidence_state": evidence_state or {},
                "evidence_requirements": selected_plan.get("evidence_requirements", []),
                "selection_rationale": selected_plan.get("reason_selected", ""),
                "trace_refs": trace_refs or {},
                "active": True,
            }
        )
        graph["nodes"][node_id] = node
        graph["active_node_id"] = node_id
        graph["counters"]["plan"] = graph["counters"].get("plan", 0) + 1

        for alternative in alternatives or []:
            alt_id = self._next_node_id(graph, "plan")
            alt_node = _base_node(
                node_id=alt_id,
                node_type="research_plan",
                mode="discovery",
                status="candidate",
                summary=_plan_summary(alternative),
            )
            alt_node.update(
                {
                    "plan_id": alternative.get("plan_id") or alt_id,
                    "role": "alternative",
                    "parent_node_id": node_id,
                    "user_question": user_question,
                    "steps": alternative.get("steps", []),
                    "evidence_requirements": alternative.get("evidence_requirements", []),
                    "why_not_selected_now": alternative.get("why_not_selected_now", ""),
                    "when_to_use": alternative.get("when_to_use", ""),
                    "active": False,
                }
            )
            graph["nodes"][alt_id] = alt_node
            graph["counters"]["plan"] = graph["counters"].get("plan", 0) + 1

        self._validate_one_active(graph)
        self._write(graph)
        return node_id

    def create_operational_node(
        self,
        *,
        user_question: str,
        plan: dict[str, Any],
        plan_ref: str | None = None,
        route_ref: str | None = None,
    ) -> str:
        graph = self._read()
        self._deactivate_active(graph, old_status="superseded")
        node_id = self._next_node_id(graph, "op")
        node = _base_node(
            node_id=node_id,
            node_type="operational_plan",
            mode="operational",
            status="active",
            summary=str(plan.get("task") or plan.get("summary") or user_question),
        )
        node.update(
            {
                "user_question": user_question,
                "route_ref": route_ref,
                "plan_path": plan_ref,
                "tool_plan_ref": plan_ref,
                "active": True,
            }
        )
        graph["nodes"][node_id] = node
        graph["active_node_id"] = node_id
        graph["counters"]["op"] = graph["counters"].get("op", 0) + 1
        self._validate_one_active(graph)
        self._write(graph)
        return node_id

    def attach_tool_plan(self, node_id: str, *, tool_plan_ref: str | None, implementation_plan_ref: str | None = None) -> None:
        graph = self._read()
        node = self._node(graph, node_id)
        if tool_plan_ref:
            node["tool_plan_ref"] = tool_plan_ref
        if implementation_plan_ref:
            node["implementation_plan_ref"] = implementation_plan_ref
        self._write(graph)

    def set_plan_refs(self, node_id: str, *, plan_ref: str | None = None, plan_json_ref: str | None = None) -> None:
        graph = self._read()
        node = self._node(graph, node_id)
        if plan_ref:
            node["plan_path"] = plan_ref
        if plan_json_ref:
            node["plan_json_path"] = plan_json_ref
        self._write(graph)

    def attach_execution(self, node_id: str, *, execution_ref: str, execution_summary_ref: str | None = None) -> None:
        graph = self._read()
        node = self._node(graph, node_id)
        refs = node.setdefault("execution_refs", [])
        if execution_ref and execution_ref not in refs:
            refs.append(execution_ref)
        if execution_summary_ref:
            node["execution_summary_path"] = execution_summary_ref
        self._write(graph)

    def attach_analyzer(self, node_id: str, *, analyzer_report_ref: str, analyzer_report_md_ref: str | None = None) -> None:
        graph = self._read()
        node = self._node(graph, node_id)
        node["analyzer_report_path"] = analyzer_report_ref
        node.setdefault("analyzer_refs", {})["parsed_report"] = analyzer_report_ref
        if analyzer_report_md_ref:
            node.setdefault("analyzer_refs", {})["report_md"] = analyzer_report_md_ref
        report = self._load_session_json(analyzer_report_ref)
        if isinstance(report, dict):
            node["latest_analyzer_verdict"] = str(report.get("result_verdict") or "").strip()
            node["latest_analyzer_summary"] = str(report.get("results_summary") or "").strip()
        self._write(graph)

    def attach_next_decision(self, node_id: str, *, decision_ref: str) -> None:
        graph = self._read()
        node = self._node(graph, node_id)
        node["next_decision_ref"] = decision_ref
        self._write(graph)

    def update_evidence_state(self, node_id: str, *, evidence_state: dict[str, Any]) -> None:
        graph = self._read()
        node = self._node(graph, node_id)
        node["evidence_state"] = evidence_state
        self._write(graph)

    def set_node_status(self, node_id: str, *, status: str, active: bool | None = None) -> None:
        graph = self._read()
        node = self._node(graph, node_id)
        node["status"] = status
        if active is not None:
            node["active"] = active
            if not active and graph.get("active_node_id") == node_id:
                graph["active_node_id"] = None
            elif active:
                self._deactivate_active(graph, old_status="superseded")
                node["active"] = True
                graph["active_node_id"] = node_id
        self._validate_one_active(graph)
        self._write(graph)

    def apply_post_analysis_decision(
        self,
        *,
        decision: dict[str, Any],
        active_plan: dict[str, Any] | None = None,
        decision_ref: str | None = None,
    ) -> str:
        graph = self._read()
        active_id = str(graph.get("active_node_id") or "")
        if not active_id:
            raise StateGraphError("Cannot apply a post-analysis decision without an active node.")
        active = self._node(graph, active_id)
        decision_type = _canonical_decision_type(decision.get("decision_type") or decision.get("decision"))
        if decision_type == "accept_and_conclude":
            active["status"] = "concluded"
            active["active"] = False
            graph["active_node_id"] = None
            self._write(graph)
            return active_id
        if decision_type == "declare_unanswerable":
            active["status"] = "unanswerable"
            active["active"] = False
            graph["active_node_id"] = None
            self._write(graph)
            return active_id
        if decision_type == "ask_user":
            active["status"] = "awaiting_user"
            self._write(graph)
            return active_id
        if decision_type == "call_panelists":
            # Legacy ScientistPanel post-analysis compatibility. The TODO4
            # MediatorAgent path uses internal callback_requests and should not
            # commit a graph transition for panelist callbacks.
            self._write(graph)
            return active_id
        next_plan = decision.get("updated_selected_research_plan")
        if isinstance(next_plan, dict) and next_plan.get("steps") and _materially_different_plan(active_plan or active, next_plan):
            parent_id = self._validated_continue_from(graph, decision.get("continue_from_node_id")) or active_id
            return self.create_branch_from_decision(
                decision=decision,
                parent_node_id=parent_id,
                decision_ref=decision_ref,
            )
        if decision_type in {"self_revise_plan", "parameter_change"}:
            active.setdefault("iterations", []).append(
                {
                    "created_at": _now(),
                    "reason": decision.get("rationale") or decision.get("reason", ""),
                    "decision_ref": decision_ref,
                }
            )
        self._write(graph)
        return active_id

    def create_branch_from_decision(
        self,
        *,
        decision: dict[str, Any],
        parent_node_id: str,
        decision_ref: str | None = None,
    ) -> str:
        graph = self._read()
        parent = self._node(graph, parent_node_id)
        next_plan = decision.get("updated_selected_research_plan")
        if not isinstance(next_plan, dict) or not next_plan.get("steps"):
            raise StateGraphError("Cannot create branch without an updated_selected_research_plan.steps list.")
        self._deactivate_active(graph, old_status="superseded")
        node_id = self._next_node_id(graph, "plan")
        node = _base_node(
            node_id=node_id,
            node_type="research_plan",
            mode="discovery",
            status="active",
            summary=_plan_summary(next_plan),
        )
        node.update(
            {
                "plan_id": next_plan.get("plan_id") or node_id,
                "role": "selected",
                "parent_node_id": parent_node_id,
                "continue_from_node_id": parent_node_id,
                "continue_from_artifact": decision.get("continue_from_artifact"),
                "transition_reason": decision.get("decision_type", ""),
                "transition_note": decision.get("transition_note", ""),
                "steps": next_plan.get("steps", []),
                "evidence_state": decision.get("evidence_state", {}),
                "selection_rationale": decision.get("rationale", ""),
                "active": True,
            }
        )
        edge = {
            "from_node_id": parent_node_id,
            "to_node_id": node_id,
            "reason": decision.get("rationale") or decision.get("reason", ""),
            "transition_reason": decision.get("decision_type", ""),
            "transition_note": decision.get("transition_note", ""),
            "continue_from_node_id": parent_node_id,
            "continue_from_artifact": decision.get("continue_from_artifact"),
            "mediator_decision_ref": decision_ref,
            "created_by": "ResearchLoop",
            "created_at": _now(),
        }
        parent.setdefault("children", []).append(node_id)
        graph["nodes"][node_id] = node
        graph["edges"].append(edge)
        graph["active_node_id"] = node_id
        graph["counters"]["plan"] = graph["counters"].get("plan", 0) + 1
        self._validate_one_active(graph)
        self._write(graph)
        return node_id

    def trajectory_context(self) -> dict[str, Any]:
        graph = self._read()
        active_id = graph.get("active_node_id")
        nodes = graph.get("nodes", {})
        active = nodes.get(active_id) if active_id else None
        tried = []
        alternatives = []
        for node in nodes.values():
            if node.get("role") == "alternative" and node.get("status") == "candidate":
                alternatives.append(
                    {
                        "node_id": node.get("node_id"),
                        "plan_id": node.get("plan_id"),
                        "summary": node.get("summary", ""),
                        "why_not_selected_before": node.get("why_not_selected_now", ""),
                        "when_to_try": node.get("when_to_use", ""),
                    }
                )
            elif node.get("node_id") != active_id and node.get("role") == "selected":
                tried.append(
                    {
                        "node_id": node.get("node_id"),
                        "summary": node.get("summary", ""),
                        "outcome": node.get("status", ""),
                        "what_was_learned": node.get("analyzer_report_path", ""),
                        "why_insufficient": node.get("next_decision_ref", ""),
                        "usable_artifacts": node.get("artifact_handles", []),
                    }
                )
        return {
            "active_node": _compact_active(active) if isinstance(active, dict) else None,
            "tried_solutions": tried,
            "untried_alternatives": alternatives,
            # Phase 8 will populate these from ArtifactRegistry and analyzer gap
            # records. They are explicit placeholders in the Phase 6 graph MVP.
            "reusable_artifacts": [],
            "unresolved_gaps": [],
        }

    def context_for_mediator(self) -> dict[str, Any]:
        return self.trajectory_context()

    def context_for_tool_consultant(self) -> dict[str, Any]:
        context = self.trajectory_context()
        active = context.get("active_node") if isinstance(context.get("active_node"), dict) else {}
        return {
            "active_node": active,
            "selected_research_plan": active.get("selected_research_plan", {}),
            "evidence_state": active.get("evidence_state", {}),
            "tried_solutions": context.get("tried_solutions", []),
            "untried_alternatives": context.get("untried_alternatives", []),
            "reusable_artifacts": context.get("reusable_artifacts", []),
            "deferred_novel_analysis_design_excluded": True,
        }

    def context_for_panelist_callback(self) -> dict[str, Any]:
        return self.trajectory_context()

    def context_for_analyzer(self) -> dict[str, Any]:
        return self.trajectory_context()

    def _validated_continue_from(self, graph: dict[str, Any], node_id: Any) -> str | None:
        if not node_id:
            return None
        node_id = str(node_id)
        if node_id not in graph.get("nodes", {}):
            raise StateGraphError(f"continue_from_node_id does not exist: {node_id}")
        return node_id

    def _node(self, graph: dict[str, Any], node_id: str) -> dict[str, Any]:
        nodes = graph.get("nodes", {})
        if node_id not in nodes:
            raise StateGraphError(f"Unknown node_id: {node_id}")
        return nodes[node_id]

    def _next_node_id(self, graph: dict[str, Any], prefix: str) -> str:
        return f"{prefix}_{graph.get('counters', {}).get(prefix, 0) + 1:03d}"

    def _deactivate_active(self, graph: dict[str, Any], *, old_status: str) -> None:
        active_id = graph.get("active_node_id")
        if active_id and active_id in graph.get("nodes", {}):
            graph["nodes"][active_id]["active"] = False
            if graph["nodes"][active_id].get("status") == "active":
                graph["nodes"][active_id]["status"] = old_status

    def _validate_one_active(self, graph: dict[str, Any]) -> None:
        active_nodes = [node_id for node_id, node in graph.get("nodes", {}).items() if node.get("active")]
        if len(active_nodes) > 1:
            raise StateGraphError(f"StateGraph has multiple active nodes: {active_nodes}")
        active_id = graph.get("active_node_id")
        if active_id and active_id not in active_nodes:
            raise StateGraphError("active_node_id does not match active node flag.")

    def _read(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return _migrate_graph(data) if isinstance(data, dict) else _empty_graph()
        except Exception:
            return _empty_graph()

    def _write(self, graph: dict[str, Any]) -> None:
        graph["updated_at"] = _now()
        self.path.write_text(json.dumps(graph, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    def _load_session_json(self, relative_path: str | None) -> Any:
        if not relative_path:
            return None
        path = self.session_dir / relative_path
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data
        except Exception:
            return None


def _empty_graph() -> dict[str, Any]:
    now = _now()
    return {
        "version": 1,
        "created_at": now,
        "updated_at": now,
        "active_node_id": None,
        "nodes": {},
        "edges": [],
        "counters": {"plan": 0, "op": 0, "conclusion": 0},
    }


def _migrate_graph(graph: dict[str, Any]) -> dict[str, Any]:
    """Normalize older persisted graph vocabulary during load."""
    for node in graph.get("nodes", {}).values():
        if not isinstance(node, dict):
            continue
        if node.get("status") == "inactive":
            node["status"] = "superseded"
        if "repeat_iterations" in node and "iterations" not in node:
            node["iterations"] = node.get("repeat_iterations") or []
    return graph


def _base_node(*, node_id: str, node_type: str, mode: str, status: str, summary: str) -> dict[str, Any]:
    return {
        "node_id": node_id,
        "node_type": node_type,
        "mode": mode,
        "status": status,
        "created_at": _now(),
        "summary": summary,
        "metadata": {},
        "route_ref": None,
        "plan_path": None,
        "plan_json_path": None,
        "tool_plan_ref": None,
        "implementation_plan_ref": None,
        "execution_refs": [],
        "analyzer_refs": {},
        "analyzer_report_path": None,
        "result_summary_path": None,
        "trace_refs": {},
        "artifact_refs_path": None,
        "artifact_handles": [],
        "children": [],
        "active": False,
    }


def _plan_summary(plan: dict[str, Any]) -> str:
    summary = str(plan.get("summary") or "").strip()
    if summary:
        return summary
    steps = plan.get("steps")
    if isinstance(steps, list) and steps:
        first = steps[0]
        if isinstance(first, dict):
            return str(first.get("biological_goal") or first.get("step") or first.get("summary") or "").strip()
        return str(first).strip()
    return ""


def _materially_different_plan(current: dict[str, Any], next_plan: dict[str, Any]) -> bool:
    current_steps = current.get("steps", [])
    next_steps = next_plan.get("steps", [])
    return json.dumps(current_steps, sort_keys=True, default=str) != json.dumps(next_steps, sort_keys=True, default=str)


def _canonical_decision_type(value: Any) -> str:
    text = str(value or "").strip()
    return {
        "conclude": "accept_and_conclude",
        "interpretation_only": "accept_and_conclude",
        "ask_user_clarification": "ask_user",
        "ask_panelist_callback": "call_panelists",
        "revise_plan": "self_revise_plan",
        "produce_next_research_plan": "self_revise_plan",
        "new_downstream_analysis": "self_revise_plan",
        "method_replacement": "self_revise_plan",
        "upstream_preprocessing_change": "self_revise_plan",
        "data_change": "self_revise_plan",
    }.get(text, text)


def _compact_active(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "node_id": node.get("node_id"),
        "summary": node.get("summary", ""),
        "status": node.get("status", ""),
        "selected_research_plan": {
            "plan_id": node.get("plan_id"),
            "summary": node.get("summary", ""),
            "steps": node.get("steps", []),
        },
        "latest_analyzer_verdict": node.get("latest_analyzer_verdict", ""),
        "analyzer_report_path": node.get("analyzer_report_path"),
        "evidence_state": node.get("evidence_state", {}),
        "artifact_handles": node.get("artifact_handles", []),
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
