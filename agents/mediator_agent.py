"""MediatorAgent — research-lead synthesis and revision modes."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

try:
    from json_repair import repair_json as _repair_json
except ImportError:
    _repair_json = None  # type: ignore[assignment]

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore[assignment]

from agents.llm_utils import single_llm_call
from agents.prompt_loader import load_updated_prompt
from agents.decision_schema import DecisionValidationError
from agents.runner import ToolCallingAgentRunner


MEDIATOR_SHARED_SYSTEM = load_updated_prompt("mediator_shared_system")
MEDIATOR_FORMULATION_PROMPT = load_updated_prompt("mediator_formulation")
MEDIATOR_ADVERSARY_REVISION_PROMPT = load_updated_prompt("mediator_adversary_revision")
MEDIATOR_POST_ANALYSIS_PROMPT = load_updated_prompt("mediator_post_analysis")

_FORMULATION_STATUSES = {"needs_panelist_callback", "ready_for_adversary"}
_POST_ANALYSIS_DECISIONS = {
    "accept_and_conclude",
    "self_revise_plan",
    "continue_with_same_research_plan",
    "ask_user",
    "declare_unanswerable",
}


class MediatorAgent:
    """Principal-investigator agent with mode-specific prompts."""

    def __init__(
        self,
        *,
        engine_name: str,
        client: Any | None = None,
        result_dir: str | Path,
        panelist_callback_executor: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
        paper_tool_specs: list[dict[str, Any]] | None = None,
        paper_tool_executor: dict[str, Callable[..., Any]] | None = None,
        max_callback_rounds_after_analysis: int = 2,
        max_schema_repair_attempts: int = 1,
    ) -> None:
        if client is None and OpenAI is None:
            raise RuntimeError("openai package is required for MediatorAgent")
        self.client = client or OpenAI()
        self.engine_name = engine_name
        self.result_dir = Path(result_dir)
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.panelist_callback_executor = panelist_callback_executor
        self.paper_tool_specs = paper_tool_specs or []
        self.paper_tool_executor = paper_tool_executor or {}
        self.max_callback_rounds_after_analysis = max(0, int(max_callback_rounds_after_analysis))
        self.max_schema_repair_attempts = max(0, int(max_schema_repair_attempts))

    def formulate(self, *, formulation_context: dict[str, Any]) -> dict[str, Any]:
        return self._run_json_mode(
            prompt=MEDIATOR_FORMULATION_PROMPT,
            context=formulation_context,
            tag="MEDIATOR_OUTPUT",
            save_name="mediator_formulation",
            validator=_normalize_formulation_output,
        )

    def synthesize_callbacks(
        self,
        *,
        formulation_context: dict[str, Any],
        callback_outputs: list[dict[str, Any]],
        round_number: int = 1,
    ) -> dict[str, Any]:
        context = dict(formulation_context)
        context["callback_outputs"] = callback_outputs
        context["callback_round_number"] = round_number
        return self._run_json_mode(
            prompt=MEDIATOR_FORMULATION_PROMPT,
            context=context,
            tag="MEDIATOR_OUTPUT",
            save_name=f"mediator_callback_synthesis_round{round_number}",
            validator=_normalize_formulation_output,
        )

    def revise_from_adversary(self, *, adversary_revision_context: dict[str, Any]) -> dict[str, Any]:
        return self._run_json_mode(
            prompt=MEDIATOR_ADVERSARY_REVISION_PROMPT,
            context=adversary_revision_context,
            tag="MEDIATOR_OUTPUT",
            save_name=f"mediator_adversary_revision_round{adversary_revision_context.get('adversary_revision_round', 0)}",
            validator=_normalize_formulation_output,
        )

    def post_analysis(self, *, post_analysis_context: dict[str, Any]) -> dict[str, Any]:
        context = dict(post_analysis_context)
        callback_findings: list[dict[str, Any]] = []
        phase_number = context.get("phase_number", 0)
        for round_number in range(0, self.max_callback_rounds_after_analysis + 1):
            result = self._run_json_mode(
                prompt=MEDIATOR_POST_ANALYSIS_PROMPT,
                context=context,
                tag="MEDIATOR_POST_ANALYSIS_OUTPUT",
                save_name=f"mediator_post_analysis_phase{phase_number}_round{round_number}",
                validator=None,
            )
            requests = _extract_panelist_callback_requests(result)
            if requests and self.panelist_callback_executor is not None and round_number < self.max_callback_rounds_after_analysis:
                round_findings = self._run_panelist_callbacks(requests=requests, round_number=round_number + 1)
                callback_findings.extend(round_findings)
                context.setdefault("panelist_callback_outputs", []).extend(round_findings)
                context.setdefault("callback_history", []).extend(round_findings)
                continue
            normalized = self._validate_with_repair(
                parsed=result,
                prompt=MEDIATOR_POST_ANALYSIS_PROMPT,
                context=context,
                tag="MEDIATOR_POST_ANALYSIS_OUTPUT",
                save_name=f"mediator_post_analysis_phase{phase_number}_round{round_number}",
                validator=_normalize_post_analysis_output,
            )
            if callback_findings:
                existing = normalized.get("panelist_callback_findings")
                normalized["panelist_callback_findings"] = (existing if isinstance(existing, list) else []) + callback_findings
            return normalized
        raise DecisionValidationError("Mediator post-analysis callback loop exhausted without a terminal decision")

    def _run_panelist_callbacks(
        self,
        *,
        requests: list[dict[str, Any]],
        round_number: int,
    ) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        for request in requests:
            role = str(request.get("role") or request.get("panelist") or "").strip().lower()
            if not role:
                continue
            try:
                output = self.panelist_callback_executor(role, {"callback": request, "round_number": round_number})
            except Exception as exc:
                output = {"callback_error": str(exc)}
            findings.append(
                {
                    "role": role,
                    "callback_type": str(request.get("callback_type") or request.get("type") or "reasoning").strip(),
                    "gap_addressed": str(request.get("gap") or request.get("assigned_gap") or request.get("question") or "").strip(),
                    "request": request,
                    "finding": output,
                }
            )
        return findings

    def _run_json_mode(
        self,
        *,
        prompt: str,
        context: dict[str, Any],
        tag: str,
        save_name: str,
        validator: Callable[[Any], dict[str, Any]] | None,
    ) -> dict[str, Any]:
        full_prompt = prompt.strip() + "\n\nCONTEXT:\n\n" + json.dumps(context, indent=2, ensure_ascii=False, default=str)
        if self.paper_tool_specs and self.paper_tool_executor:
            runner = ToolCallingAgentRunner(
                model=self.engine_name,
                system_prompt=MEDIATOR_SHARED_SYSTEM,
                tool_specs=self.paper_tool_specs,
                tool_executor=self.paper_tool_executor,
                transcript_path=str(self.result_dir / f"{save_name}_transcript.jsonl"),
                tool_trace_path=str(self.result_dir / f"{save_name}_tool_trace.jsonl"),
                client=self.client,
                max_iterations=8,
                max_tool_calls=4,
            )
            text = runner.run(
                initial_user_input=full_prompt,
                response_handler=lambda t: _tag_done_handler(t, tag),
            )
        else:
            text = single_llm_call(self.client, self.engine_name, full_prompt, system=MEDIATOR_SHARED_SYSTEM)
        parsed = _extract_tag_json(str(text), tag)
        self._save(save_name, {"context": context, "raw": text, "parsed": parsed})
        if validator is None:
            return parsed
        return self._validate_with_repair(
            parsed=parsed,
            prompt=prompt,
            context=context,
            tag=tag,
            save_name=save_name,
            validator=validator,
        )

    def _validate_with_repair(
        self,
        *,
        parsed: dict[str, Any],
        prompt: str,
        context: dict[str, Any],
        tag: str,
        save_name: str,
        validator: Callable[[Any], dict[str, Any]],
    ) -> dict[str, Any]:
        current = parsed
        for attempt in range(self.max_schema_repair_attempts + 1):
            try:
                return validator(current)
            except DecisionValidationError as exc:
                if attempt >= self.max_schema_repair_attempts:
                    raise
                repair_prompt = _build_repair_prompt(
                    original_prompt=prompt,
                    context=context,
                    tag=tag,
                    invalid_output=current,
                    error=str(exc),
                )
                repair_text = single_llm_call(self.client, self.engine_name, repair_prompt, system=MEDIATOR_SHARED_SYSTEM)
                current = _extract_tag_json(str(repair_text), tag)
                self._save(
                    f"{save_name}_schema_repair{attempt + 1}",
                    {"context": context, "error": str(exc), "raw": repair_text, "parsed": current},
                )
        raise DecisionValidationError("Schema repair failed")

    def _save(self, name: str, data: Any) -> None:
        path = self.result_dir / f"{name}.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def _extract_tag_json(text: str, tag: str) -> dict[str, Any]:
    aliases = {
        "MEDIATOR_OUTPUT": ["MEDIATOR_OUTPUT", "MEDIATOR"],
        "MEDIATOR_POST_ANALYSIS_OUTPUT": ["MEDIATOR_POST_ANALYSIS_OUTPUT", "MEDIATOR_POST_ANALYSIS", "POST_ANALYSIS_DECISION"],
    }
    candidates = aliases.get(tag, [tag])
    for candidate in [*candidates, tag.upper(), tag.lower()]:
        match = re.search(rf"<{re.escape(candidate)}>(.*?)</{re.escape(candidate)}>", text, re.DOTALL)
        if not match:
            continue
        raw = match.group(1).strip()
        fence = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
        if fence:
            raw = fence.group(1).strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            repaired = re.sub(r'("|\]|\})\s*\n(\s*")', r'\1,\n\2', raw)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError as exc:
                if _repair_json is not None:
                    try:
                        return json.loads(_repair_json(raw))
                    except Exception:
                        pass
                return {"raw": raw, "parse_error": str(exc)}
    return {"raw": text, "parse_error": f"No <{tag}> block found"}


def _tag_done_handler(text: str, tag: str) -> dict[str, Any]:
    if f"<{tag}>" in str(text) and f"</{tag}>" in str(text):
        return {"done": True, "result": text}
    return {
        "done": False,
        "next_user_input": f"Your response must contain a <{tag}>...</{tag}> JSON block. Please produce it now.",
    }


def _normalize_formulation_output(value: Any) -> dict[str, Any]:
    out = dict(value) if isinstance(value, dict) else {"raw": str(value), "parse_error": "not a dict"}
    if out.get("parse_error"):
        raise DecisionValidationError(str(out.get("parse_error")))
    status = str(out.get("formulation_status") or "").strip()
    if status not in _FORMULATION_STATUSES:
        raise DecisionValidationError(f"formulation_status must be one of {sorted(_FORMULATION_STATUSES)}")
    out["formulation_status"] = status
    out.setdefault("callback_requests", [])
    out.setdefault("limitations", [])
    out.setdefault("research_gap_resolution", [])
    out.setdefault("evidence_completeness", "partial")
    out.setdefault("callback_budget_exhausted", False)
    if status == "ready_for_adversary":
        if not isinstance(out.get("selected_research_plan"), dict):
            raise DecisionValidationError("ready_for_adversary requires selected_research_plan")
        out.setdefault(
            "trajectory_decision",
            {"action": "initialize_plan", "branch_from_node_id": None, "reason": "candidate plan ready for adversarial review"},
        )
    return out


def _normalize_post_analysis_output(value: Any) -> dict[str, Any]:
    out = dict(value) if isinstance(value, dict) else {"raw": str(value), "parse_error": "not a dict"}
    if out.get("parse_error"):
        raise DecisionValidationError(str(out.get("parse_error")))
    decision = str(out.get("decision") or out.get("decision_type") or "").strip()
    if decision not in _POST_ANALYSIS_DECISIONS:
        raise DecisionValidationError(f"decision must be one of {sorted(_POST_ANALYSIS_DECISIONS)}")
    out["decision"] = decision
    out["decision_type"] = decision
    out.setdefault("rationale", "")
    out.setdefault("evidence_state", {})
    out.setdefault("research_gap_resolution", [])
    out.setdefault("panelist_callback_findings", [])
    out.setdefault("clarifying_questions", [])
    out.setdefault("overall_confidence", 0.0)
    return out


def _extract_panelist_callback_requests(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        return []
    requests = (
        value.get("callback_requests")
        or value.get("panelist_callback_requests")
        or value.get("internal_tool_requests")
        or []
    )
    decision = str(value.get("decision") or value.get("decision_type") or "").strip()
    if decision != "needs_panelist_callback" and not requests:
        return []
    if not isinstance(requests, list):
        return []
    return [item for item in requests if isinstance(item, dict)]


def _build_repair_prompt(
    *,
    original_prompt: str,
    context: dict[str, Any],
    tag: str,
    invalid_output: dict[str, Any],
    error: str,
) -> str:
    return (
        "Your previous structured output had a schema or JSON error. Fix it.\n\n"
        f"Error: {error}\n\n"
        "STRICT OUTPUT RULES:\n"
        f"- Output ONLY: <{tag}>{{...}}</{tag}>\n"
        "- The content inside the tags must be valid JSON. No trailing commas. "
        "All string values must be properly quoted and escaped. "
        "All keys must be quoted. No comments.\n"
        "- Zero prose before or after the tags.\n\n"
        "Invalid output to fix:\n"
        f"{json.dumps(invalid_output, indent=2, ensure_ascii=False, default=str)}\n\n"
        "Original task prompt (for schema reference):\n"
        f"{original_prompt.strip()}"
    )
