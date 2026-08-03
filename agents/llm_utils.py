"""Shared LLM utility functions used across agent modules."""

from __future__ import annotations

from typing import Any


def single_llm_call(
    client: Any,
    engine_name: str,
    prompt: str,
    *,
    system: str = "",
) -> str:
    """Make a single non-streaming LLM call via the OpenAI responses API.

    Works with both OpenAI and compatible clients. Handles both
    `output_text` shortcut and iterating `output` items as fallback.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system.strip()})
    messages.append({"role": "user", "content": prompt.strip()})

    response = client.responses.create(model=engine_name, input=messages)

    text = str(getattr(response, "output_text", "") or "").strip()
    if text:
        return text

    for item in getattr(response, "output", []):
        content = getattr(item, "content", None)
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list):
            for part in content:
                t = getattr(part, "text", None)
                if isinstance(t, str) and t.strip():
                    return t.strip()

    return ""
