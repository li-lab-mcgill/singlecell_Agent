"""AdversarialPanelist — critic-only stress test for candidate research plans.

The TODO4 flow keeps revision ownership with MediatorAgent. This class reviews a
single uncommitted candidate plan plus its context, retrieves adversarial
literature if useful, and returns a verdict with critique. It does not defend,
remediate, or mutate the plan.

Usage:
    adversary = AdversarialPanelist(
        engine_name="gpt-4o",
        fast_engine_name="gpt-4o-mini",
        retriever=retriever,
        judge=judge,
        paper_md_writer=writer,    # optional
        client=client,
        result_dir="results/panel",
        max_rounds=3,
    )
    result = adversary.run(
        user_question="...",
        mediator_plan=initial_plan,   # dict from ScientistPanel mediator
    )
    # result["verdict"]  → "survives" | "needs_revision" | "unsalvageable"
    # result["plan"]     → updated plan dict (or original if survives/unsalvageable)
    # result["rounds"]   → number of challenge rounds completed
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore[assignment]

from agents.llm_utils import single_llm_call
from agents.panelist_tools import build_panelist_tool_registry
from agents.paper_judge import PaperJudge
from agents.runner import ToolCallingAgentRunner
from agents.decision_schema import DecisionValidationError
from rag.literature_retriever import LiteratureRetriever
from prompts.adversarial_prompts import (
    ADVERSARIAL_SYSTEM,
    ADVERSARIAL_ALIGNMENT_PROMPT,
    ADVERSARIAL_CHALLENGE_PROMPT,
)

class AdversarialPanelist:
    """Stress-tests the Mediator's draft plan and returns critique only.

    Args:
        engine_name:       Main LLM for adversary, re-mediator, and defenses.
        fast_engine_name:  Fast LLM for tool calls (literature retrieval).
        retriever:         Shared LiteratureRetriever instance.
        judge:             PaperJudge instance.
        paper_md_writer:   PaperMDWriter (optional — for wiki growth during adversarial retrieval).
        client:            OpenAI-compatible client.
        result_dir:        Directory for saved challenge/defense/re-mediator JSON files.
        max_rounds:        Compatibility budget read by ResearchLoop. This class
                           performs one critique per run call.
    """

    def __init__(
        self,
        *,
        engine_name: str,
        fast_engine_name: str | None = None,
        retriever: LiteratureRetriever,
        judge: PaperJudge,
        paper_md_writer: Any | None = None,
        client: Any | None = None,
        result_dir: str | Path,
        max_rounds: int = 3,
        max_schema_repair_attempts: int = 1,
    ):
        if client is None and OpenAI is None:
            raise RuntimeError("openai package is required for AdversarialPanelist")
        self.client = client or OpenAI()
        self.engine_name = engine_name
        self.fast_engine_name = fast_engine_name or engine_name
        self.retriever = retriever
        self.judge = judge
        self.paper_md_writer = paper_md_writer
        self.result_dir = Path(result_dir)
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.max_rounds = max_rounds
        self.max_schema_repair_attempts = max(0, int(max_schema_repair_attempts))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        *,
        adversary_context: dict[str, Any] | None = None,
        user_question: str | None = None,
        mediator_plan: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run one adversarial critique.

        Returns:
            {
              "verdict":       "survives" | "needs_revision" | "unsalvageable",
              "plan":          <final plan dict>,
              "rounds":        1,
              "last_challenge": <structured challenge>,
            }
        """
        if adversary_context is None:
            adversary_context = {
                "user_question": user_question or "",
                "candidate_plan": mediator_plan or {},
                "candidate_trajectory_decision": {},
            }
        user_question = str(adversary_context.get("user_question") or user_question or "")
        current_plan = adversary_context.get("candidate_plan") or mediator_plan or {}
        challenge = self._run_challenge(
            adversary_context=adversary_context,
            user_question=user_question,
            mediator_plan=current_plan,
            round_num=1,
        )
        self._save("adversarial_challenge", challenge)
        verdict = str(challenge["verdict"]).strip()
        return {
            "verdict": verdict,
            "adversary_verdict": verdict,
            "plan": current_plan,
            "rounds": 1,
            "debate_log": [
                {
                    "round": 1,
                    "verdict": verdict,
                    "n_challenges": len(challenge.get("challenges", [])),
                    "summary": challenge.get("summary", ""),
                    "recommended_revision": challenge.get("recommended_revision", ""),
                }
            ],
            "last_challenge": challenge,
            "critique_summary": challenge.get("summary", ""),
            "failure_modes": challenge.get("challenges", []),
            "required_revisions": challenge.get("recommended_revision", ""),
            "fatal_flaws": [
                item for item in challenge.get("challenges", [])
                if isinstance(item, dict) and item.get("severity") == "fatal"
            ],
        }

    def review_alignment(
        self,
        *,
        user_question: str,
        research_plan: dict[str, Any],
        tool_plan: dict[str, Any] | None = None,
        implementation_plan: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Review whether executable plans satisfy the selected research plan."""
        prompt = ADVERSARIAL_ALIGNMENT_PROMPT.format(
            user_question=user_question,
            research_plan=json.dumps(research_plan or {}, indent=2, ensure_ascii=False),
            tool_plan=json.dumps(tool_plan or {}, indent=2, ensure_ascii=False),
            implementation_plan=json.dumps(implementation_plan or {}, indent=2, ensure_ascii=False),
        )
        text = single_llm_call(self.client, self.engine_name, prompt, system=ADVERSARIAL_SYSTEM.strip())
        return _normalize_alignment_review(_extract_tag_json(text, "ALIGNMENT_REVIEW"))

    # ------------------------------------------------------------------
    # Step 1: Adversary challenge (with tool use)
    # ------------------------------------------------------------------

    def _run_challenge(
        self,
        *,
        adversary_context: dict[str, Any],
        user_question: str,
        mediator_plan: dict[str, Any],
        round_num: int,
    ) -> dict[str, Any]:
        """Run the adversary agent with retrieve_literature access."""
        plan_str = json.dumps(mediator_plan, indent=2, ensure_ascii=False)
        prompt = ADVERSARIAL_CHALLENGE_PROMPT.format(
            user_question=user_question,
            mediator_plan=plan_str,
            adversary_context=json.dumps(adversary_context, indent=2, ensure_ascii=False, default=str),
            debate_history="(critic-only run; prior critiques are included in FULL ADVERSARY CONTEXT when available)",
        )

        # Adversary uses retrieve_literature with role="adversary"
        registry = build_panelist_tool_registry(
            role="adversary",
            retriever=self.retriever,
            judge=self.judge,
            paper_md_writer=self.paper_md_writer,
        )
        runner = ToolCallingAgentRunner(
            model=self.fast_engine_name,
            system_prompt=ADVERSARIAL_SYSTEM.strip(),
            tool_specs=registry.tool_specs(),
            tool_executor=registry.executor(),
            transcript_path=str(self.result_dir / f"adversary_round{round_num}_transcript.jsonl"),
            tool_trace_path=str(self.result_dir / f"adversary_round{round_num}_tool_trace.jsonl"),
            client=self.client,
            max_iterations=12,
            max_tool_calls=8,
        )
        text = runner.run(
            initial_user_input=prompt,
            response_handler=lambda t: _challenge_done_handler(t),
        )
        parsed = _extract_tag_json(_ensure_str(text), "CHALLENGE")
        return self._validate_challenge_with_repair(
            parsed=parsed,
            prompt=prompt,
            adversary_context=adversary_context,
            round_num=round_num,
        )

    def _validate_challenge_with_repair(
        self,
        *,
        parsed: dict[str, Any],
        prompt: str,
        adversary_context: dict[str, Any],
        round_num: int,
    ) -> dict[str, Any]:
        current = parsed
        for attempt in range(self.max_schema_repair_attempts + 1):
            try:
                return _validate_challenge_output(current)
            except DecisionValidationError as exc:
                if attempt >= self.max_schema_repair_attempts:
                    raise
                repair_prompt = _build_schema_repair_prompt(
                    original_prompt=prompt,
                    tag="CHALLENGE",
                    invalid_output=current,
                    schema_error=str(exc),
                )
                repair_text = single_llm_call(self.client, self.engine_name, repair_prompt, system=ADVERSARIAL_SYSTEM.strip())
                current = _extract_tag_json(_ensure_str(repair_text), "CHALLENGE")
                self._save(
                    f"adversarial_challenge_round{round_num}_schema_repair{attempt + 1}",
                    {
                        "adversary_context": adversary_context,
                        "schema_error": str(exc),
                        "raw": repair_text,
                        "parsed": current,
                    },
                )
        raise DecisionValidationError("Adversarial challenge schema repair failed")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _save(self, name: str, data: Any) -> None:
        path = self.result_dir / f"{name}.json"
        payload = data if isinstance(data, (dict, list)) else {"raw": str(data)}
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _ensure_str(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _extract_tag_json(text: str, tag: str) -> dict[str, Any]:
    pattern = rf"<{tag}>(.*?)</{tag}>"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return {"raw": text, "parse_error": f"No <{tag}> block found"}
    raw = match.group(1).strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    if fence:
        raw = fence.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Attempt comma-repair
        repaired = re.sub(r'("|\]|\})\s*\n(\s*")', r'\1,\n\2', raw)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            return {"raw": raw, "parse_error": "JSON decode failed"}


_ADVERSARY_VERDICTS = {"survives", "needs_revision", "unsalvageable"}
_ALIGNMENT_FAILURE_MODES = {
    "none",
    "weak_evidence",
    "missing_analysis",
    "invalid_statistical_unit",
    "overclaim",
    "missing_control",
    "tool_mismatch",
    "alternative_explanation",
    "literature_mismatch",
    "retention_gap",
}
_ALIGNMENT_TARGETS = {
    "research_plan",
    "tool_plan",
    "implementation_plan",
    "panelist_reasoning",
    "mediator_synthesis",
}


def _validate_challenge_output(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise DecisionValidationError("CHALLENGE payload must be a JSON object")
    out = dict(payload)
    if out.get("parse_error"):
        raise DecisionValidationError(str(out.get("parse_error")))
    verdict = str(out.get("verdict") or "").strip()
    if verdict not in _ADVERSARY_VERDICTS:
        raise DecisionValidationError(f"verdict must be one of {sorted(_ADVERSARY_VERDICTS)}")
    out["verdict"] = verdict
    out.setdefault("summary", "")
    out.setdefault("recommended_revision", "")
    out["challenges"] = _list_or_empty(out.get("challenges"))
    return out


def _build_schema_repair_prompt(
    *,
    original_prompt: str,
    tag: str,
    invalid_output: Any,
    schema_error: str,
) -> str:
    return (
        f"The previous response did not satisfy the required schema.\n\n"
        f"Schema error:\n{schema_error}\n\n"
        f"Required output:\n"
        f"<{tag}>\n"
        "{\n"
        '  "verdict": "survives | needs_revision | unsalvageable",\n'
        '  "summary": "short critique summary",\n'
        '  "challenges": [],\n'
        '  "recommended_revision": "specific revision if needed"\n'
        "}\n"
        f"</{tag}>\n\n"
        f"Original task prompt:\n{original_prompt}\n\n"
        f"Invalid parsed output:\n{json.dumps(invalid_output, indent=2, ensure_ascii=False, default=str)}\n\n"
        "Return only the corrected tagged JSON block."
    )


def _normalize_alignment_review(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        payload = {"raw": _ensure_str(payload), "parse_error": "Alignment review was not JSON"}
    out = dict(payload)
    verdict = str(out.get("verdict") or "").strip()
    out["verdict"] = verdict if verdict in _ADVERSARY_VERDICTS else "needs_revision"
    failure_mode = str(out.get("failure_mode") or "").strip()
    out["failure_mode"] = failure_mode if failure_mode in _ALIGNMENT_FAILURE_MODES else (
        "none" if out["verdict"] == "survives" else "weak_evidence"
    )
    target = str(out.get("target") or "").strip()
    out["target"] = target if target in _ALIGNMENT_TARGETS else "tool_plan"
    out.setdefault("core_critique", "")
    out.setdefault("weakest_assumption", "")
    out.setdefault("required_revision", "")
    out["questions_for_panelists"] = _list_or_empty(out.get("questions_for_panelists"))
    out["questions_for_toolconsultant"] = _list_or_empty(out.get("questions_for_toolconsultant"))
    out.setdefault("reasoning_trace_summary", "")
    return out


def _list_or_empty(value: Any) -> list[Any]:
    return value if isinstance(value, list) else ([] if value is None else [value])


def _challenge_done_handler(text: str) -> dict[str, Any]:
    """Response handler: done when <CHALLENGE>...</CHALLENGE> is present."""
    if "<CHALLENGE>" in text and "</CHALLENGE>" in text:
        return {"done": True, "result": text}
    return {
        "done": False,
        "next_user_input": (
            "Your response must contain a <CHALLENGE>...</CHALLENGE> block "
            "with your structured JSON output. Please produce it now."
        ),
    }
