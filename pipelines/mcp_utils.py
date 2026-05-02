import json
from typing import Any, Dict, List, Optional

import requests


def _parse_mcp_response_text(text: str) -> Optional[Dict[str, Any]]:
    """
    MCP server may return SSE-like text. Try to extract JSON payload.
    """
    if not text:
        return None
    if text.lstrip().startswith("{"):
        try:
            return json.loads(text)
        except Exception:
            return None
    # SSE format: lines with "data: {json}"
    data_lines = [line[len("data: "):] for line in text.splitlines() if line.startswith("data: ")]
    if not data_lines:
        return None
    try:
        return json.loads(data_lines[-1])
    except Exception:
        return None


def fetch_mcp_tools_text(
    url: str = "https://Paper2Agent-scanpy-mcp.hf.space/mcp",
    timeout: int = 10,
    max_tools: int = 50,
    max_chars: int = 4000,
) -> str:
    """
    Initialize MCP session, list tools, and return a concise text summary.
    Returns '(unavailable)' on any failure.
    """
    try:
        headers = {"Accept": "application/json, text/event-stream"}
        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "mcp-client", "version": "0.1"},
            },
        }
        init_resp = requests.post(url, json=init_payload, headers=headers, timeout=timeout)
        session_id = init_resp.headers.get("Mcp-Session-Id") or init_resp.headers.get("mcp-session-id")
        if not session_id:
            init_data = _parse_mcp_response_text(init_resp.text)
            if init_data:
                session_id = init_data.get("result", {}).get("sessionId")
        if session_id:
            headers["Mcp-Session-Id"] = session_id

        payload = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
        data = _parse_mcp_response_text(resp.text)
        tools = (data or {}).get("result", {}).get("tools", [])
        if not tools:
            return "(unavailable)"

        lines: List[str] = []
        for t in tools[:max_tools]:
            name = t.get("name") if isinstance(t, dict) else getattr(t, "name", "")
            desc = t.get("description") if isinstance(t, dict) else getattr(t, "description", "")
            if desc:
                lines.append(f"- {name}: {desc}")
            else:
                lines.append(f"- {name}")

        out = "MCP Tools:\n" + "\n".join(lines)
        if len(out) > max_chars:
            out = out[: max_chars - 3] + "..."
        return out
    except Exception:
        return "(unavailable)"
