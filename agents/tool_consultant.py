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
from agents.wiki_tools import build_wiki_tool_registry
from backend.objectives import list_objectives
from backend.tools.executor import build_wiki_executor_registry
from prompts.tool_consultant_prompts import (
    TOOL_CONSULTANT_DECISION_PROMPT,
    TOOL_CONSULTANT_OUTPUT_SCHEMA_PROMPT,
    TOOL_CONSULTANT_SYSTEM_PROMPT,
    WIKI_SCHEMA_PROMPT,
)


class ToolConsultantAgent:
    """Plan-only first-stage agent for tool/coder/research dispatch.

    When long_term_memory is provided, prior experience from earlier sessions is
    injected into the planning prompt — enabling experience-guided planning.
    """

    def __init__(
        self,
        *,
        engine_name: str,
        result_dir: str | Path,
        backend: Any | None = None,
        client: Any | None = None,
        long_term_memory: Any | None = None,
    ):
        self.engine_name = engine_name
        self.result_dir = Path(result_dir) / "feedback"
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.backend = backend
        self.client = client
        self.long_term_memory = long_term_memory  # LongTermMemory instance or None

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
        available_stages = build_wiki_executor_registry().keys()

        # Build wiki tool registry — always available regardless of backend
        wiki_registry = build_wiki_tool_registry()

        # Inject prior experience from long-term memory (if available)
        prior_experience = ""
        if self.long_term_memory is not None:
            data_summary = session_state.get("data_summary")
            prior_experience = self.long_term_memory.format_prior_experience(
                user_question=str(user_message or ""),
                data_summary=data_summary,
                max_sessions=3,
            )

        decision_prompt = (
            TOOL_CONSULTANT_DECISION_PROMPT.strip()
            + "\n\nUSER REQUEST:\n\n" + str(user_message or "").strip()
            + "\n\nSESSION STATE:\n\n" + json.dumps(session_state, indent=2, ensure_ascii=False)
            + "\n\nPREVIOUS PLAN TYPE:\n\n" + previous_plan_type
            + "\n\nPREVIOUS PLAN:\n\n" + previous_plan
            + "\n\nAVAILABLE OBJECTIVES:\n\n" + json.dumps(list_objectives(), indent=2, ensure_ascii=False)
            + (("\n\n" + prior_experience) if prior_experience else "")
        )
        prompt = "\n\n".join(
            [
                decision_prompt,
                TOOL_CONSULTANT_OUTPUT_SCHEMA_PROMPT.strip(),
            ]
        )

        system_prompt = "\n\n".join([
            TOOL_CONSULTANT_SYSTEM_PROMPT.strip(),
            WIKI_SCHEMA_PROMPT.strip(),
        ])

        runner = ToolCallingAgentRunner(
            model=self.engine_name,
            system_prompt=system_prompt,
            tool_specs=wiki_registry.tool_specs(),
            tool_executor=wiki_registry.executor(),
            transcript_path=str(self.result_dir / f"{session_tag}_transcript.jsonl"),
            tool_trace_path=str(self.result_dir / f"{session_tag}_tool_trace.jsonl"),
            client=self.client,
            max_iterations=25,
            max_tool_calls=40,
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


