"""Deterministic conversation-level registry for task-scoped research states."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.research_state import ResearchState
from agents.session_recorder import SessionRecorder
from agents.state_graph import StateGraphManager


@dataclass
class ResearchWorkspaceResolution:
    research_state: ResearchState
    decision: dict[str, Any]


class ResearchWorkspace:
    """Owns the active research-state registry for one frontend conversation.

    This first version is intentionally deterministic. It chooses whether a
    discovery turn continues the active research state or creates a new one
    using simple follow-up/new-task cues, and it stores the decision in a small
    workspace registry on disk.
    """

    def __init__(
        self,
        *,
        root_dir: str | Path,
        conversation_id: str = "C001",
    ) -> None:
        self.root_dir = Path(root_dir)
        self.conversation_id = _clean_id(conversation_id) or "C001"
        self.path = self.root_dir / "research_workspace.json"
        self.root_dir.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(
                {
                    "conversation_id": self.conversation_id,
                    "active_research_state_id": None,
                    "research_state_registry": {},
                    "created_at": _now(),
                    "updated_at": _now(),
                }
            )

    def resolve_research_state(
        self,
        *,
        user_message: str,
        resolved_intent: str,
        data_summary: dict[str, Any] | str,
        session_context: dict[str, Any] | None = None,
    ) -> ResearchWorkspaceResolution:
        workspace = self._read()
        registry = workspace.setdefault("research_state_registry", {})
        active_id = workspace.get("active_research_state_id")
        action = "create_new"
        reason = "no active research state exists"

        if active_id and active_id in registry:
            text = f"{user_message}\n{resolved_intent}".lower()
            if _looks_like_new_task(text):
                action = "create_new"
                reason = "message explicitly asks for a new or separate research task"
            elif _looks_like_switch_request(text):
                matched = _match_registry_state(text, registry)
                if matched:
                    active_id = matched
                    action = "switch_active"
                    reason = "message refers to a previous research state"
                else:
                    action = "continue_active"
                    reason = "switch requested but no better deterministic match was found"
            else:
                action = "continue_active"
                reason = "existing active research state is reused by default for discovery follow-up"

        if action == "create_new":
            active_id = _next_state_id(registry)
            registry[active_id] = {
                "research_state_id": active_id,
                "user_task": resolved_intent or user_message,
                "original_user_message": user_message,
                "short_summary": _short_summary(resolved_intent or user_message),
                "status": "active",
                "created_at": _now(),
                "updated_at": _now(),
                "related_research_state_ids": [],
            }
        else:
            registry[active_id]["updated_at"] = _now()
            registry[active_id]["status"] = "active"

        workspace["active_research_state_id"] = active_id
        workspace["updated_at"] = _now()
        self._write(workspace)

        recorder = SessionRecorder(
            root_dir=self.root_dir,
            conversation_id=self.conversation_id,
            session_id=active_id,
        )
        graph = StateGraphManager(session_dir=recorder.session_dir)
        state = ResearchState(
            user_question=resolved_intent or user_message,
            data_summary=data_summary,
            recorder=recorder,
            graph=graph,
            research_state_id=active_id,
            original_user_message=user_message,
            resolved_intent=resolved_intent or user_message,
            session_context=session_context or {},
        )
        _hydrate_state_from_graph(state)
        decision = {
            "action": action,
            "reason": reason,
            "research_state_id": active_id,
            "conversation_id": self.conversation_id,
            "registry_path": str(self.path),
        }
        recorder.save_json("route/research_workspace_decision.json", decision)
        return ResearchWorkspaceResolution(research_state=state, decision=decision)

    def _read(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write(self, workspace: dict[str, Any]) -> None:
        workspace["updated_at"] = _now()
        self.path.write_text(json.dumps(workspace, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def _hydrate_state_from_graph(state: ResearchState) -> None:
    graph = state.graph.graph
    nodes = graph.get("nodes", {}) if isinstance(graph, dict) else {}
    active_id = graph.get("active_node_id") if isinstance(graph, dict) else None
    node = nodes.get(active_id) if active_id else None
    if not isinstance(node, dict):
        selected_nodes = [
            item for item in nodes.values()
            if isinstance(item, dict) and item.get("role") == "selected"
        ]
        selected_nodes.sort(key=lambda item: str(item.get("created_at") or ""))
        node = selected_nodes[-1] if selected_nodes else None
        active_id = node.get("node_id") if isinstance(node, dict) else None
    if isinstance(node, dict):
        state.active_node_id = str(active_id) if active_id else None
        plan = node.get("selected_research_plan")
        if isinstance(plan, dict):
            state.selected_research_plan = plan
        else:
            state.selected_research_plan = {
                "plan_id": node.get("plan_id") or state.active_node_id,
                "summary": node.get("summary", ""),
                "steps": node.get("steps", []),
            }
        evidence_state = node.get("evidence_state")
        if isinstance(evidence_state, dict):
            state.evidence_state = evidence_state


def _looks_like_new_task(text: str) -> bool:
    markers = (
        "new task",
        "separate task",
        "separate analysis",
        "different question",
        "start over",
        "start a new",
        "unrelated",
    )
    return any(marker in text for marker in markers)


def _looks_like_switch_request(text: str) -> bool:
    markers = ("go back", "return to", "switch back", "previous result", "that result")
    return any(marker in text for marker in markers)


def _match_registry_state(text: str, registry: dict[str, Any]) -> str | None:
    for state_id, entry in registry.items():
        haystack = " ".join(
            str(entry.get(key) or "").lower()
            for key in ("research_state_id", "user_task", "short_summary")
        )
        if state_id.lower() in text or any(token and token in text for token in haystack.split()[:8]):
            return state_id
    return None


def _next_state_id(registry: dict[str, Any]) -> str:
    existing = []
    for key in registry:
        text = str(key)
        if text.startswith("S") and text[1:].isdigit():
            existing.append(int(text[1:]))
    return f"S{(max(existing) + 1) if existing else 1:03d}"


def _short_summary(text: str, limit: int = 180) -> str:
    clean = " ".join(str(text or "").split())
    return clean[:limit]


def _clean_id(value: str | None) -> str:
    return str(value or "").strip().replace("/", "_").replace(" ", "_")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
