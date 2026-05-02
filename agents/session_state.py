from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict


class SessionStateStore:
    """Persistent structured state for the local frontend session."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def snapshot(self) -> Dict[str, Any]:
        return copy.deepcopy(self.data)

    def history(self, *, limit: int = 8) -> list[dict[str, str]]:
        history = self.data.get("history", [])
        if not isinstance(history, list):
            return []
        return copy.deepcopy(history[-limit:])

    def set_initial_query(self, query: str) -> None:
        if not self.data.get("initial_query"):
            self.data["initial_query"] = str(query or "").strip()
            self.save()

    def begin_turn(self, *, user_message: str, session_tag: str) -> None:
        history = self.data.setdefault("history", [])
        if not isinstance(history, list):
            history = []
            self.data["history"] = history
        history.append(
            {
                "role": "user",
                "content": str(user_message or "").strip(),
                "session_tag": str(session_tag or "").strip(),
                "status": "in_progress",
            }
        )
        self.data["current_turn"] = {
            "session_tag": str(session_tag or "").strip(),
            "user_message": str(user_message or "").strip(),
            "status": "in_progress",
        }
        self.save()

    def record_turn(self, *, user_message: str, payload: Dict[str, Any]) -> None:
        history = self.data.setdefault("history", [])
        if not isinstance(history, list):
            history = []
            self.data["history"] = history
        result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
        failed = _payload_indicates_error(payload)
        if history and _is_pending_user_turn(history[-1], user_message):
            history[-1]["status"] = "failed" if failed else "completed"
        else:
            history.append(
                {
                    "role": "user",
                    "content": str(user_message or "").strip(),
                    "status": "failed" if failed else "completed",
                }
            )
        assistant_item = {"role": "assistant", "content": _assistant_history_text(payload)}
        if failed:
            assistant_item["status"] = "failed"
        history.append(assistant_item)

        route = payload.get("route") if isinstance(payload.get("route"), dict) else {}
        decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}

        self.data["last_route"] = route
        self.data["last_result"] = result
        if payload.get("task_execution_path"):
            self.data["last_task_execution_path"] = payload["task_execution_path"]
        if route.get("route_path"):
            self.data["last_route_path"] = route["route_path"]

        if decision:
            self.data["last_decision"] = decision
        artifacts = _collect_artifacts(result)
        if artifacts:
            self.data["last_artifacts"] = artifacts
        all_h5ad = _find_all_nested(result, "output_h5ad_path")
        active_h5ad = all_h5ad[-1] if all_h5ad else (artifacts.get("output_h5ad_path") if artifacts else None)
        if active_h5ad:
            self.data["active_h5ad_path"] = active_h5ad
        self.data["active_embedding_key"] = _find_nested(result, "embedding_key") or self.data.get("active_embedding_key")
        self.data["active_cluster_key"] = _find_nested(result, "cluster_key") or self.data.get("active_cluster_key")
        self.data["active_work_type"] = _active_work_type(route, decision, result) or self.data.get("active_work_type")
        self.data["current_turn"] = None
        self.data["last_error"] = _error_summary(result) if failed else None
        self.save()

    def record_error(self, *, user_message: str, error: str) -> None:
        history = self.data.setdefault("history", [])
        if not isinstance(history, list):
            history = []
            self.data["history"] = history
        if history and _is_pending_user_turn(history[-1], user_message):
            history[-1]["status"] = "failed"
        else:
            history.append({"role": "user", "content": str(user_message or "").strip(), "status": "failed"})
        message = str(error or "Unknown error").strip()
        history.append({"role": "assistant", "content": message, "status": "failed"})
        self.data["last_result"] = {"status": "failed", "error": message}
        self.data["last_error"] = message
        self.data["current_turn"] = None
        self.save()

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")

    def reset(self) -> None:
        self.data = _with_defaults({})
        self.save()

    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return _with_defaults(data)
            except Exception:
                pass
        return _with_defaults({})


def _with_defaults(data: Dict[str, Any]) -> Dict[str, Any]:
    data.setdefault("history", [])
    data.setdefault("initial_query", None)
    data.setdefault("last_route", None)
    data.setdefault("last_decision", None)
    data.setdefault("last_result", None)
    data.setdefault("last_artifacts", {})
    data.setdefault("active_work_type", None)
    data.setdefault("active_h5ad_path", None)
    data.setdefault("active_embedding_key", None)
    data.setdefault("active_cluster_key", None)
    data.setdefault("current_turn", None)
    data.setdefault("last_error", None)
    data.setdefault("last_task_execution_path", None)
    return data


def _is_pending_user_turn(item: Dict[str, Any], user_message: str) -> bool:
    return (
        item.get("role") == "user"
        and item.get("status") == "in_progress"
        and str(item.get("content") or "").strip() == str(user_message or "").strip()
    )


def assistant_display_text(payload: Dict[str, Any]) -> str:
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    for key in ("message", "search_summary", "recommendation"):
        if result.get(key):
            return str(result[key])
    error = _error_summary(result)
    if error:
        return error

    status = str(result.get("status") or payload.get("status") or "completed").strip()
    artifacts = _collect_artifacts(result)
    parts: list[str] = []
    if status:
        parts.append(f"Status: {status}.")
    if result.get("objective_name"):
        parts.append(f"Objective: {result['objective_name']}.")
    if result.get("trials_run") is not None:
        parts.append(f"Trials run: {result['trials_run']}.")
    if artifacts:
        artifact_text = ", ".join(f"{key}: {value}" for key, value in sorted(artifacts.items())[:4])
        parts.append(f"Artifacts: {artifact_text}.")
    if result.get("tool_calls_used"):
        parts.append(f"Tools used: {', '.join(str(item) for item in result['tool_calls_used'])}.")
    return " ".join(parts) if parts else "Completed without a text response."


def _assistant_history_text(payload: Dict[str, Any]) -> str:
    return assistant_display_text(payload)


def _payload_indicates_error(payload: Dict[str, Any]) -> bool:
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    return bool(_error_summary(result))


def _error_summary(result: Dict[str, Any]) -> str:
    status = str(result.get("status") or "").strip().lower()
    if status in {"error", "failed", "failure"}:
        message = result.get("error") or result.get("message") or "The previous run reported an error."
        return f"Error: {message}"
    for key in ("error", "stderr"):
        if result.get(key):
            return f"Error: {str(result[key]).strip()}"
    stdout = str(result.get("stdout") or "")
    if "error" in stdout.lower():
        line = _first_error_line(stdout)
        return f"Error reported in script output: {line}"
    attempts = result.get("attempts")
    if isinstance(attempts, list) and attempts:
        latest = attempts[-1]
        if isinstance(latest, dict):
            execution = latest.get("execution_result")
            if isinstance(execution, dict):
                nested = {
                    "status": "failed" if execution.get("returncode") not in (None, 0) else execution.get("status"),
                    "error": execution.get("stderr") or execution.get("error"),
                    "stdout": execution.get("stdout"),
                }
                return _error_summary(nested)
    nested_result = result.get("last_result")
    if isinstance(nested_result, dict):
        nested_summary = _error_summary(nested_result)
        if nested_summary:
            return nested_summary
    return ""


def _first_error_line(text: str) -> str:
    for line in text.splitlines():
        if "error" in line.lower():
            clean = line.strip()
            return clean[:500] if clean else "error"
    return text.strip()[:500] or "error"


def _collect_artifacts(result: Dict[str, Any]) -> Dict[str, Any]:
    artifacts: Dict[str, Any] = {}
    for key in ("best_artifacts", "artifacts", "artifact_paths"):
        value = result.get(key)
        if isinstance(value, dict):
            artifacts.update(value)
    raw_results = result.get("raw_results")
    if isinstance(raw_results, dict):
        dag_result = raw_results.get("dag_result")
        if isinstance(dag_result, dict):
            best_path = dag_result.get("best_path")
            if isinstance(best_path, dict):
                best_artifacts = best_path.get("artifacts")
                if isinstance(best_artifacts, dict):
                    artifacts.update(best_artifacts)
                if best_path.get("path_dir"):
                    artifacts["path_dir"] = best_path["path_dir"]
    for key in ("output_h5ad_path", "script_path", "report_path", "trace_path", "artifact_dir"):
        if result.get(key):
            artifacts[key] = result[key]
    last_result = result.get("last_result")
    if isinstance(last_result, dict):
        for key in ("output_h5ad_path", "plot_path", "figure_path"):
            if last_result.get(key):
                artifacts[key] = last_result[key]
    return artifacts


def _find_nested(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        if key in value:
            return value[key]
        for child in value.values():
            found = _find_nested(child, key)
            if found is not None:
                return found
    if isinstance(value, list):
        for child in value:
            found = _find_nested(child, key)
            if found is not None:
                return found
    return None


def _find_all_nested(value: Any, key: str) -> list[Any]:
    """Collect ALL values for *key* via DFS, preserving encounter order."""
    results: list[Any] = []
    if isinstance(value, dict):
        if key in value:
            results.append(value[key])
        for child in value.values():
            results.extend(_find_all_nested(child, key))
    if isinstance(value, list):
        for child in value:
            results.extend(_find_all_nested(child, key))
    return results


def _active_work_type(route: Dict[str, Any], decision: Dict[str, Any], result: Dict[str, Any]) -> str | None:
    if decision.get("dag_plan") or result.get("best_path") or result.get("dag_summary") or _find_nested(result, "best_path"):
        return "dag"
    if decision.get("implementation_plan") or result.get("script_path"):
        return "coder"
    if decision.get("research_brief"):
        return "research"
    return None
