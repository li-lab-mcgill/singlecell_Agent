from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from agents.decision_schema import (
    DecisionValidationError,
    extract_json_payload,
    validate_tool_consultant_decision,
)
from agents.runner import ToolCallingAgentRunner
from backend.objectives import list_objectives
from agents.tools import build_tool_executor_registry
from prompts.tool_consultant_prompts import (
    TOOL_CONSULTANT_DECISION_PROMPT,
    TOOL_CONSULTANT_OUTPUT_SCHEMA_PROMPT,
    TOOL_CONSULTANT_SYSTEM_PROMPT,
)


class ToolConsultantAgent:
    """Plan-only first-stage agent for tool/coder/research dispatch."""

    def __init__(
        self,
        *,
        engine_name: str,
        result_dir: str | Path,
        backend: Any | None = None,
        client: Any | None = None,
    ):
        self.engine_name = engine_name
        self.result_dir = Path(result_dir) / "feedback"
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.backend = backend
        self.client = client

    def decide(
        self,
        *,
        user_message: str,
        session_state: Dict[str, Any] | None = None,
        session_tag: str = "tool_consultant",
    ) -> Dict[str, Any]:
        session_state = dict(session_state or {})
        previous_plan = str(session_state.get("previous_plan") or "<none>")
        previous_plan_type = str(session_state.get("previous_plan_type") or "none").strip() or "none"
        tool_docs = "<no backend provided>"
        available_stages = None
        if self.backend is not None:
            tool_docs = _load_tool_docs(self.result_dir)
            available_stages = build_tool_executor_registry(self.backend).executor().keys()

        prompt = "\n\n".join(
            [
                TOOL_CONSULTANT_DECISION_PROMPT.format(
                    user_message=str(user_message or "").strip(),
                    session_state=json.dumps(session_state, indent=2, ensure_ascii=False),
                    previous_plan=previous_plan,
                    previous_plan_type=previous_plan_type,
                    objective_registry=json.dumps(list_objectives(), indent=2, ensure_ascii=False),
                    tool_docs=tool_docs,
                ).strip(),
                TOOL_CONSULTANT_OUTPUT_SCHEMA_PROMPT.strip(),
            ]
        )

        runner = ToolCallingAgentRunner(
            model=self.engine_name,
            system_prompt=TOOL_CONSULTANT_SYSTEM_PROMPT,
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
                payload = extract_json_payload(text, "TOOL_DECISION")
                decision = validate_tool_consultant_decision(payload, available_stages=available_stages)
            except DecisionValidationError as exc:
                return {
                    "done": False,
                    "next_user_input": f"Your TOOL_DECISION was invalid: {exc}. Return exactly one valid TOOL_DECISION JSON payload.",
                }
            out_path = self.result_dir / f"{session_tag}_decision.json"
            out_path.write_text(json.dumps(decision, indent=2, ensure_ascii=False), encoding="utf-8")
            decision["decision_path"] = str(out_path)
            return {"done": True, "result": decision}

        return runner.run(initial_user_input=prompt, response_handler=_handle_response)


def _load_tool_docs(result_dir: Path) -> str:
    repo_root = result_dir.resolve().parents[1]
    doc_path = repo_root / "docs" / "tool_docs_draft.md"
    try:
        text = doc_path.read_text(encoding="utf-8").strip()
    except Exception:
        return f"<tool documentation unavailable: {doc_path}>"
    return text or f"<tool documentation empty: {doc_path}>"
