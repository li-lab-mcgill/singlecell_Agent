from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from agents.decision_schema import DecisionValidationError, extract_json_payload
from agents.runner import ToolCallingAgentRunner
from prompts.session_router_prompts import (
    SESSION_ROUTER_PROMPT,
    SESSION_ROUTER_SCHEMA_PROMPT,
    SESSION_ROUTER_SYSTEM_PROMPT,
)


VALID_SESSION_ROUTES = {
    "direct_response",
    "task",
}


class SessionRouter:
    """Classify a frontend chat turn before invoking task-planning agents."""

    def __init__(
        self,
        *,
        engine_name: str,
        result_dir: str | Path,
        client: Any | None = None,
    ):
        self.engine_name = engine_name
        self.result_dir = Path(result_dir) / "feedback"
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.client = client

    def route(
        self,
        *,
        user_message: str,
        session_state: Dict[str, Any] | None = None,
        session_tag: str = "session_router",
    ) -> Dict[str, Any]:
        prompt = "\n\n".join(
            [
                SESSION_ROUTER_PROMPT.format(
                    user_message=str(user_message or "").strip(),
                    session_state=json.dumps(session_state or {}, indent=2, ensure_ascii=False),
                ).strip(),
                SESSION_ROUTER_SCHEMA_PROMPT.strip(),
            ]
        )
        runner = ToolCallingAgentRunner(
            model=self.engine_name,
            system_prompt=SESSION_ROUTER_SYSTEM_PROMPT,
            tool_specs=[],
            tool_executor={},
            transcript_path=str(self.result_dir / f"{session_tag}_transcript.jsonl"),
            tool_trace_path=str(self.result_dir / f"{session_tag}_tool_trace.jsonl"),
            client=self.client,
            max_iterations=4,
            max_tool_calls=0,
        )

        def _handle_response(text: str) -> Dict[str, Any]:
            try:
                payload = extract_json_payload(text, "SESSION_ROUTE")
                route = validate_session_route(payload)
            except DecisionValidationError as exc:
                return {
                    "done": False,
                    "next_user_input": (
                        f"Your SESSION_ROUTE was invalid: {exc}. "
                        "Return exactly one valid SESSION_ROUTE JSON payload."
                    ),
                }
            out_path = self.result_dir / f"{session_tag}_route.json"
            out_path.write_text(json.dumps(route, indent=2, ensure_ascii=False), encoding="utf-8")
            route["route_path"] = str(out_path)
            return {"done": True, "result": route}

        return runner.run(initial_user_input=prompt, response_handler=_handle_response)


def validate_session_route(payload: Dict[str, Any]) -> Dict[str, Any]:
    route = str(payload.get("route") or "").strip()
    if route not in VALID_SESSION_ROUTES:
        raise DecisionValidationError(f"route must be one of {sorted(VALID_SESSION_ROUTES)}")
    response = payload.get("response")
    if response is not None:
        response = str(response).strip()
    return {
        "resolved_intent": str(payload.get("resolved_intent") or "").strip(),
        "route": route,
        "reason": str(payload.get("reason") or "").strip(),
        "response": response or None,
        "requires_artifact_lookup": bool(payload.get("requires_artifact_lookup", False)),
    }
