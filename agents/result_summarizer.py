from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from agents.runner import ToolCallingAgentRunner
from prompts.result_summarizer_prompts import RESULT_SUMMARIZER_PROMPT, RESULT_SUMMARIZER_SYSTEM_PROMPT


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".svg", ".webp"}


class ResultSummarizer:
    """Format raw executor results into a concise user-facing response."""

    def __init__(self, *, engine_name: str, result_dir: str | Path, client: Any | None = None):
        self.engine_name = engine_name
        self.result_dir = Path(result_dir) / "feedback"
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.client = client

    def summarize(
        self,
        *,
        user_query: str,
        decision: Dict[str, Any],
        raw_results: Dict[str, Any],
        session_tag: str = "result_summarizer",
    ) -> Dict[str, Any]:
        figures = _collect_figures(raw_results)
        prompt = RESULT_SUMMARIZER_PROMPT.format(
            user_query=str(user_query or "").strip(),
            decision_summary=json.dumps(_slim_decision(decision), indent=2, ensure_ascii=False),
            raw_results=json.dumps(_slim_results(raw_results), indent=2, ensure_ascii=False),
        )
        runner = ToolCallingAgentRunner(
            model=self.engine_name,
            system_prompt=RESULT_SUMMARIZER_SYSTEM_PROMPT,
            tool_specs=[],
            tool_executor={},
            transcript_path=str(self.result_dir / f"{session_tag}_transcript.jsonl"),
            tool_trace_path=str(self.result_dir / f"{session_tag}_tool_trace.jsonl"),
            client=self.client,
            max_iterations=2,
            max_tool_calls=0,
        )

        def _handle(text: str) -> Dict[str, Any]:
            return {"done": True, "result": {"message": str(text or "").strip(), "figures": figures}}

        return runner.run(initial_user_input=prompt, response_handler=_handle)


def _slim_decision(decision: Dict[str, Any]) -> Dict[str, Any]:
    return _slim(decision, max_list_items=8, max_str=1200)


def _slim_results(raw_results: Dict[str, Any]) -> Dict[str, Any]:
    return _slim(raw_results, max_list_items=12, max_str=2000)


def _slim(obj: Any, *, max_list_items: int, max_str: int) -> Any:
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, value in obj.items():
            if key in {"attempt_log", "trace", "stdout", "stderr"}:
                out[key] = _short(value, max_str)
            else:
                out[str(key)] = _slim(value, max_list_items=max_list_items, max_str=max_str)
        return out
    if isinstance(obj, list):
        trimmed = obj[:max_list_items]
        out = [_slim(item, max_list_items=max_list_items, max_str=max_str) for item in trimmed]
        if len(obj) > max_list_items:
            out.append(f"... {len(obj) - max_list_items} more item(s)")
        return out
    return _short(obj, max_str) if isinstance(obj, str) else obj


def _short(value: Any, max_chars: int) -> str:
    text = str(value or "")
    return text if len(text) <= max_chars else text[:max_chars] + f"... <truncated {len(text) - max_chars} chars>"


def _collect_figures(raw_results: Dict[str, Any]) -> list[str]:
    figures: list[str] = []
    seen: set[str] = set()
    _walk_for_images(raw_results, figures, seen)
    return figures


def _walk_for_images(obj: Any, out: list[str], seen: set[str]) -> None:
    if isinstance(obj, str):
        path = Path(obj)
        if path.suffix.lower() in IMAGE_SUFFIXES and path.exists():
            resolved = str(path)
            if resolved not in seen:
                seen.add(resolved)
                out.append(resolved)
    elif isinstance(obj, dict):
        for value in obj.values():
            _walk_for_images(value, out, seen)
    elif isinstance(obj, list):
        for value in obj:
            _walk_for_images(value, out, seen)
