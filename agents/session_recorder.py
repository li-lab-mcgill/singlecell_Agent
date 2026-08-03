from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SessionRecorder:
    """Session-centered storage helper for research and operational runs.

    The recorder owns the Phase 6 directory layout, common metadata files, and
    progress.jsonl. Components still create their own detailed payloads, but
    they write through this helper so paths are stable and comparable.
    """

    def __init__(
        self,
        *,
        root_dir: str | Path,
        conversation_id: str | None = None,
        session_id: str | None = None,
    ):
        self.root_dir = Path(root_dir)
        self.conversation_id = _clean_id(conversation_id) or _next_id(self.root_dir / "conversations", "C")
        self.conversation_dir = self.root_dir / "conversations" / self.conversation_id
        self.session_id = _clean_id(session_id) or _next_id(self.conversation_dir / "sessions", "S")
        self.session_dir = self.conversation_dir / "sessions" / self.session_id
        self.progress_path = self.session_dir / "progress.jsonl"
        self.session_path = self.session_dir / "session.json"
        self.conversation_path = self.conversation_dir / "conversation.json"
        self.leaderboard_path = self.conversation_dir / "leaderboard.json"
        self._ensure_layout()
        self._ensure_metadata()

    def start_turn(self, *, user_message: str, turn_id: str | None = None) -> str:
        turn_id = _clean_id(turn_id) or f"turn_{len(self._session().get('message_history', [])) + 1:03d}"
        session = self._session()
        session.setdefault("message_history", []).append(
            {
                "turn_id": turn_id,
                "role": "user",
                "content": str(user_message or "").strip(),
                "created_at": _now(),
            }
        )
        session["status"] = "in_progress"
        self._write_session(session)
        self.append_progress("user_message", "User message received.", {"turn_id": turn_id})
        return turn_id

    def set_status(self, status: str, **extra: Any) -> None:
        session = self._session()
        session["status"] = str(status or "").strip() or "unknown"
        session.update(extra)
        self._write_session(session)
        self.append_progress("session_status", f"Session status: {session['status']}.", extra)

    def set_active_node(self, node_id: str | None) -> None:
        session = self._session()
        session["active_node_id"] = node_id
        self._write_session(session)

    def set_final_response(self, ref: str) -> None:
        session = self._session()
        session["final_response_ref"] = ref
        self._write_session(session)

    def save_json(self, relative_path: str | Path, data: Any) -> str:
        path = self.session_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        return self.relpath(path)

    def save_text(self, relative_path: str | Path, text: str) -> str:
        path = self.session_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(text or ""), encoding="utf-8")
        return self.relpath(path)

    def append_progress(self, event_type: str, message: str, refs: dict[str, Any] | None = None) -> None:
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "timestamp": _now(),
            "event_type": str(event_type or "event"),
            "message": str(message or ""),
            "refs": refs or {},
        }
        with self.progress_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")

    def node_dir(self, node_id: str) -> Path:
        path = self.session_dir / "nodes" / node_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def execution_dir(self, execution_id: str) -> Path:
        path = self.session_dir / "executions" / execution_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def relpath(self, path: str | Path) -> str:
        return str(Path(path).resolve().relative_to(self.session_dir.resolve()))

    def _ensure_layout(self) -> None:
        for relative in (
            ".",
            "route",
            "clarification",
            "nodes",
            "traces/router",
            "traces/panelists",
            "traces/mediator",
            "traces/adversary",
            "traces/tool_consultant",
            "traces/analyzer",
            "traces/summarizer",
            "traces/responder",
            "executions",
            "artifacts/files",
            "reports",
        ):
            (self.session_dir / relative).mkdir(parents=True, exist_ok=True)

    def _ensure_metadata(self) -> None:
        conversation = _load_json(self.conversation_path, default={})
        conversation.setdefault("conversation_id", self.conversation_id)
        conversation.setdefault("created_at", _now())
        conversation["latest_session_id"] = self.session_id
        self.conversation_path.write_text(json.dumps(conversation, indent=2, ensure_ascii=False), encoding="utf-8")

        leaderboard = _load_json(self.leaderboard_path, default={})
        leaderboard.setdefault("conversation_id", self.conversation_id)
        leaderboard.setdefault("created_at", _now())
        leaderboard.setdefault("updated_at", _now())
        leaderboard.setdefault("nodes", [])
        self.leaderboard_path.write_text(json.dumps(leaderboard, indent=2, ensure_ascii=False), encoding="utf-8")

        session = _load_json(self.session_path, default={})
        session.setdefault("session_id", self.session_id)
        session.setdefault("conversation_id", self.conversation_id)
        session.setdefault("created_at", _now())
        session.setdefault("status", "initialized")
        session.setdefault("message_history", [])
        session.setdefault("active_node_id", None)
        session.setdefault("active_artifacts", [])
        session.setdefault("route_ref", None)
        session.setdefault("final_response_ref", None)
        self._write_session(session)

        if not self.progress_path.exists():
            self.progress_path.write_text("", encoding="utf-8")

    def _session(self) -> dict[str, Any]:
        return _load_json(self.session_path, default={})

    def _write_session(self, session: dict[str, Any]) -> None:
        self.session_path.write_text(json.dumps(session, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def _load_json(path: Path, *, default: Any) -> Any:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, type(default)) else default
        except Exception:
            return default
    return default


def _next_id(parent: Path, prefix: str) -> str:
    parent.mkdir(parents=True, exist_ok=True)
    existing = []
    for path in parent.iterdir():
        name = path.name
        if name.startswith(prefix) and name[len(prefix):].isdigit():
            existing.append(int(name[len(prefix):]))
    return f"{prefix}{(max(existing) + 1) if existing else 1:03d}"


def _clean_id(value: str | None) -> str:
    text = str(value or "").strip()
    return text.replace("/", "_").replace(" ", "_")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
