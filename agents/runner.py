from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List

from dotenv import load_dotenv

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - exercised via runtime environment
    OpenAI = None  # type: ignore[assignment]

load_dotenv()


def _as_dict(item: Any) -> Dict[str, Any]:
    if isinstance(item, dict):
        return item
    data = {}
    for key in ["type", "id", "name", "arguments", "call_id", "content", "role", "text"]:
        if hasattr(item, key):
            data[key] = getattr(item, key)
    return data


def _item_type(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("type", "")).strip()
    return str(getattr(item, "type", "")).strip()


def _response_id(response: Any) -> str:
    return str(getattr(response, "id", "") or "")


def _response_output(response: Any) -> List[Any]:
    output = getattr(response, "output", None)
    return list(output) if isinstance(output, list) else []


def _message_text(item: Any) -> str:
    payload = _as_dict(item)
    content = payload.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts: List[str] = []
        for part in content:
            part_dict = _as_dict(part)
            if isinstance(part, dict):
                if "text" in part and isinstance(part["text"], str):
                    texts.append(part["text"])
                elif isinstance(part.get("text"), dict):
                    text_value = part["text"].get("value")
                    if isinstance(text_value, str):
                        texts.append(text_value)
            else:
                text_value = getattr(part, "text", None)
                if isinstance(text_value, str):
                    texts.append(text_value)
                elif hasattr(text_value, "value") and isinstance(text_value.value, str):
                    texts.append(text_value.value)
                elif isinstance(part_dict.get("text"), str):
                    texts.append(part_dict["text"])
        return "\n".join(texts).strip()
    return ""


def _response_text(response: Any) -> str:
    text = str(getattr(response, "output_text", "") or "").strip()
    if text:
        return text
    parts: List[str] = []
    for item in _response_output(response):
        if _item_type(item) == "message":
            value = _message_text(item)
            if value:
                parts.append(value)
    return "\n".join(parts).strip()


def _function_calls(response: Any) -> List[Dict[str, Any]]:
    calls: List[Dict[str, Any]] = []
    for item in _response_output(response):
        if _item_type(item) != "function_call":
            continue
        payload = _as_dict(item)
        calls.append(
            {
                "call_id": str(payload.get("call_id", "") or ""),
                "name": str(payload.get("name", "") or ""),
                "arguments": str(payload.get("arguments", "") or "{}"),
            }
        )
    return calls


def _append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


class ToolCallingAgentRunner:
    def __init__(
        self,
        *,
        model: str,
        system_prompt: str,
        tool_specs: List[Dict[str, Any]],
        tool_executor: Dict[str, Callable[..., Any]],
        transcript_path: str,
        tool_trace_path: str,
        client: Any | None = None,
        temperature: float = 0.2,
        max_iterations: int = 24,
        max_tool_calls: int = 24,
    ):
        if client is None and OpenAI is None:
            raise RuntimeError("openai package is required for tool-calling agents")
        self.client = client or OpenAI()
        self.model = model
        self.system_prompt = system_prompt.strip()
        self.tool_specs = tool_specs
        self.tool_executor = tool_executor
        self.transcript_path = Path(transcript_path)
        self.tool_trace_path = Path(tool_trace_path)
        self.temperature = temperature
        self.max_iterations = max_iterations
        self.max_tool_calls = max_tool_calls

    def _create_response(self, *, input_payload: Any, previous_response_id: str | None = None) -> Any:
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "input": input_payload,
            "tools": self.tool_specs,
            "parallel_tool_calls": False,
        }
        if previous_response_id:
            kwargs["previous_response_id"] = previous_response_id
        return self.client.responses.create(**kwargs)

    def run(self, *, initial_user_input: str, response_handler: Callable[[str], Dict[str, Any]]) -> Any:
        self.transcript_path.parent.mkdir(parents=True, exist_ok=True)
        self.tool_trace_path.parent.mkdir(parents=True, exist_ok=True)
        self.transcript_path.write_text("", encoding="utf-8")
        self.tool_trace_path.write_text("", encoding="utf-8")

        _append_jsonl(self.transcript_path, {"role": "system", "content": self.system_prompt})
        _append_jsonl(self.transcript_path, {"role": "user", "content": initial_user_input})

        response = self._create_response(
            input_payload=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": initial_user_input},
            ]
        )

        tool_calls_used = 0
        for _ in range(self.max_iterations):
            text = _response_text(response)
            if text:
                _append_jsonl(self.transcript_path, {"role": "assistant", "content": text})

            calls = _function_calls(response)
            if calls:
                if tool_calls_used + len(calls) > self.max_tool_calls:
                    raise RuntimeError("Tool call budget exceeded")
                tool_outputs = []
                for call in calls:
                    tool_calls_used += 1
                    try:
                        args = json.loads(call["arguments"] or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    if not isinstance(args, dict):
                        args = {}
                    fn = self.tool_executor.get(call["name"])
                    if fn is None:
                        result: Any = {"error": f"Unknown tool: {call['name']}"}
                    else:
                        try:
                            result = fn(**args)
                        except Exception as exc:  # pragma: no cover - runtime safety
                            result = {"error": str(exc)}
                    _append_jsonl(
                        self.tool_trace_path,
                        {
                            "tool_name": call["name"],
                            "arguments": args,
                            "result": result,
                        },
                    )
                    _append_jsonl(
                        self.transcript_path,
                        {
                            "role": "tool",
                            "tool_name": call["name"],
                            "arguments": args,
                            "content": result,
                        },
                    )
                    tool_outputs.append(
                        {
                            "type": "function_call_output",
                            "call_id": call["call_id"],
                            "output": json.dumps(result, ensure_ascii=False),
                        }
                    )
                response = self._create_response(
                    input_payload=tool_outputs,
                    previous_response_id=_response_id(response) or None,
                )
                continue

            directive = response_handler(text)
            if directive.get("done"):
                return directive.get("result")
            next_user_input = str(directive.get("next_user_input", "") or "").strip()
            if not next_user_input:
                raise RuntimeError("Response handler must provide next_user_input or done=True")
            _append_jsonl(self.transcript_path, {"role": "user", "content": next_user_input})
            response = self._create_response(
                input_payload=[{"role": "user", "content": next_user_input}],
                previous_response_id=_response_id(response) or None,
            )

        raise RuntimeError("Agent loop exceeded max_iterations")
