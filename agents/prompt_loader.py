"""Prompt loading helpers for markdown prompts under updated_prompts/."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_UPDATED_PROMPTS_DIR = _PROJECT_ROOT / "updated_prompts"


@lru_cache(maxsize=64)
def load_updated_prompt(name: str, *, fallback: str = "") -> str:
    """Load a markdown prompt and return the fenced prompt body when present."""
    path = _UPDATED_PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        return fallback
    text = path.read_text(encoding="utf-8")
    fence = re.search(r"```\s*\n(.*?)\n```", text, re.DOTALL)
    return (fence.group(1).strip() if fence else text.strip()) or fallback


@lru_cache(maxsize=8)
def load_scientist_panel_schemas() -> dict[str, Any]:
    """Load the ScientistPanel schema set from updated_prompts."""
    path = _UPDATED_PROMPTS_DIR / "scientist_panel_schemas.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}
