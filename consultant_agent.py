from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from agent_runner import ToolCallingAgentRunner
from agent_tools import build_consultant_registry
from consultant import (
    _extract_tag_payload,
    format_implementation_plan_text,
    format_prior_plan_text,
    validate_candidate_comparison,
    validate_implementation_plan,
    validate_prior_decision_payload,
)
from consultant_prompts import (
    CONSULTANT_CANDIDATE_STAGE_PROMPT,
    CONSULTANT_IMPLEMENTATION_PLAN_PROMPT,
    CONSULTANT_PRIOR_DECISION_PROMPT,
    CONSULTANT_TOOL_USE_PROMPT,
)


class ConsultantAgent:
    def __init__(
        self,
        *,
        engine_name: str,
        paper_store: Any,
        result_dir: str,
        single_cell_backend: Any | None = None,
        client: Any | None = None,
    ):
        self.engine_name = engine_name
        self.paper_store = paper_store
        self.result_dir = Path(result_dir) / "feedback"
        self.single_cell_backend = single_cell_backend
        self.client = client
        self.system_prompt = "\n\n".join(
            [
                CONSULTANT_TOOL_USE_PROMPT.strip(),
                CONSULTANT_CANDIDATE_STAGE_PROMPT.strip(),
                CONSULTANT_PRIOR_DECISION_PROMPT.strip(),
                CONSULTANT_IMPLEMENTATION_PLAN_PROMPT.strip(),
            ]
        )

    def generate_plan(self, *, background: str, evaluation_guidance: Dict[str, Any], session_tag: str = "consultant") -> Dict[str, Any]:
        state: Dict[str, Any] = {
            "candidate_comparison": None,
            "prior_decision": None,
            "implementation_plan": None,
        }
        registry = build_consultant_registry(self.paper_store, single_cell_backend=self.single_cell_backend)
        runner = ToolCallingAgentRunner(
            model=self.engine_name,
            system_prompt=self.system_prompt,
            tool_specs=registry.tool_specs(),
            tool_executor=registry.executor(),
            transcript_path=str(self.result_dir / f"{session_tag}_transcript.jsonl"),
            tool_trace_path=str(self.result_dir / f"{session_tag}_tool_trace.jsonl"),
            client=self.client,
        )
        initial_prompt = (
            "Design the implementation plan for this task.\n\n"
            f"BACKGROUND:\n{background.strip()}\n\n"
            "The analyst has produced the following evaluation plan:\n"
            f"{json.dumps(evaluation_guidance, indent=2, ensure_ascii=False)}\n\n"
            "Use tools to inspect the dataset, priors, and literature. "
            "First emit <CANDIDATE_COMPARISON>, then <PRIOR_DECISION>, then <IMPLEMENTATION_PLAN>."
        )

        def _save_artifact(name: str, payload: Dict[str, Any]) -> None:
            (self.result_dir / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        def _handle_response(text: str) -> Dict[str, Any]:
            stripped = str(text or "").strip()
            if not stripped:
                return {
                    "done": False,
                    "next_user_input": "No milestone was provided. Continue and emit the next required milestone.",
                }

            try:
                if state["candidate_comparison"] is None and "<CANDIDATE_COMPARISON>" in stripped:
                    payload = json.loads(_extract_tag_payload(stripped, "CANDIDATE_COMPARISON"))
                    state["candidate_comparison"] = validate_candidate_comparison(payload)
                    _save_artifact("candidate_comparison.json", state["candidate_comparison"])
                if state["candidate_comparison"] is not None and state["prior_decision"] is None and "<PRIOR_DECISION>" in stripped:
                    payload = json.loads(_extract_tag_payload(stripped, "PRIOR_DECISION"))
                    state["prior_decision"] = validate_prior_decision_payload(payload)
                    _save_artifact("prior_decision.json", state["prior_decision"])
                if state["candidate_comparison"] is not None and state["prior_decision"] is not None and state["implementation_plan"] is None and "<IMPLEMENTATION_PLAN>" in stripped:
                    payload = json.loads(_extract_tag_payload(stripped, "IMPLEMENTATION_PLAN"))
                    state["implementation_plan"] = validate_implementation_plan(payload)
                    _save_artifact("implementation_plan.json", state["implementation_plan"])
            except Exception as exc:
                return {
                    "done": False,
                    "next_user_input": f"Your last milestone output was invalid. Fix the JSON and milestone structure. Validation error: {exc}",
                }

            if state["candidate_comparison"] is None:
                return {
                    "done": False,
                    "next_user_input": (
                        "You must emit <CANDIDATE_COMPARISON> first as valid JSON with at least 3 candidate approaches."
                    ),
                }
            if state["prior_decision"] is None:
                return {
                    "done": False,
                    "next_user_input": (
                        "Candidate comparison recorded. Continue using tools if needed, then emit <PRIOR_DECISION> as valid JSON. "
                        "Include prior_schema inside that payload."
                    ),
                }
            if state["implementation_plan"] is None:
                return {
                    "done": False,
                    "next_user_input": (
                        "Prior decision recorded. Continue using tools if needed, then emit <IMPLEMENTATION_PLAN> as valid JSON."
                    ),
                }

            return {
                "done": True,
                "result": {
                    "candidate_comparison": state["candidate_comparison"],
                    "prior_decision": state["prior_decision"],
                    "implementation_plan": state["implementation_plan"],
                    "prior_plan_text": format_prior_plan_text(state["prior_decision"]),
                    "implementation_plan_text": format_implementation_plan_text(state["implementation_plan"]),
                },
            }

        return runner.run(initial_user_input=initial_prompt, response_handler=_handle_response)
