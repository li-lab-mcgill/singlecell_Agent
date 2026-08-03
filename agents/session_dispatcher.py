from __future__ import annotations

import copy
import inspect
import json
import re
from pathlib import Path
from typing import Any, Dict

from agents.session_router import SessionRouter
from agents.session_state import SessionStateStore


class SessionDispatcher:
    """Route frontend turns and execute task branches directly."""

    def __init__(
        self,
        *,
        router: SessionRouter | None,
        tool_consultant: Any,
        coder: Any,
        research_executor: Any | None,
        tool_artifact_dir: str | Path,
        state_store: SessionStateStore,
        result_dir: str | Path,
        dag_executor: Any | None = None,
        result_summarizer: Any | None = None,
        research_loop: Any | None = None,
        research_workspace: Any | None = None,
    ):
        self.router = router
        self.tool_consultant = tool_consultant
        self.dag_executor = dag_executor
        self.coder = coder
        self.research_executor = research_executor
        self.result_summarizer = result_summarizer
        self.research_loop = research_loop
        self.research_workspace = research_workspace
        self.tool_artifact_dir = Path(tool_artifact_dir)
        self.tool_artifact_dir.mkdir(parents=True, exist_ok=True)
        self.state_store = state_store
        self.result_dir = Path(result_dir)
        self.feedback_dir = self.result_dir / "feedback"
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
        self.responder = DeterministicResponder(state_store)

    def handle(
        self,
        *,
        user_message: str,
        session_state: Dict[str, Any] | None = None,
        session_tag: str = "session",
    ) -> Dict[str, Any]:
        session_state = dict(session_state or {})
        session_state["persistent_session"] = _trim_persistent_session(self.state_store.snapshot())
        if self.router is None:
            raise RuntimeError("SessionDispatcher.handle requires a router.")
        route = self.router.route(
            user_message=user_message,
            session_state=session_state,
            session_tag=f"{session_tag}_session_router",
        )
        route_name = route["route"]

        if route_name == "direct_response":
            payload = self._handle_direct_response(route)
        elif route_name == "task":
            intent_mode = route.get("intent_mode", "ambiguous")
            planning_state = self._build_task_session_state(session_state)
            resolved_message = route.get("resolved_intent") or user_message
            if intent_mode == "ambiguous":
                payload = self._handle_ambiguous_task(
                    user_message=resolved_message,
                    route=route,
                )
            elif intent_mode == "discovery":
                payload = self._handle_research_task(
                    user_message=resolved_message,
                    original_user_message=user_message,
                    session_state=planning_state,
                    session_tag=session_tag,
                    route=route,
                )
            else:
                payload = self._handle_task(
                    user_message=resolved_message,
                    session_state=planning_state,
                    session_tag=session_tag,
                )
        else:  # pragma: no cover - router validation prevents this
            payload = {"decision": {}, "result": {"status": "failed", "error": f"Unknown route: {route_name}"}}

        payload.setdefault("decision", {})
        payload.setdefault("result", {})
        payload["route"] = route
        payload["tool_artifact_dir"] = str(self.tool_artifact_dir)
        out_path = self.feedback_dir / f"{session_tag}_session_dispatch.json"
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        payload["route_dispatch_path"] = str(out_path)
        return payload

    def _handle_direct_response(self, route: Dict[str, Any]) -> Dict[str, Any]:
        return self.responder.respond(route)

    def _handle_ambiguous_task(
        self,
        *,
        user_message: str,
        route: Dict[str, Any],
    ) -> Dict[str, Any]:
        message = (
            "I need to clarify the goal before running analysis.\n\n"
            "Option 1: Treat this as operational execution: run a known workflow and produce files.\n"
            "Option 2: Treat this as discovery: form a research plan, evaluate evidence, and interpret scientific claims.\n\n"
            "Please choose one interpretation, and I will continue from there."
        )
        return {
            "decision": {
                "route": "clarification_required",
                "intent_mode": "ambiguous",
                "execution_path": "clarification",
                "resolved_intent": user_message,
                "router_reason": route.get("reason", ""),
            },
            "result": {
                "status": "needs_input",
                "loop_status": "awaiting_user",
                "message": message,
                "images": [],
                "execution_path": "clarification",
            },
        }

    def _handle_task(
        self,
        *,
        user_message: str,
        session_state: Dict[str, Any] | None = None,
        session_tag: str = "session",
    ) -> Dict[str, Any]:
        return self.execute_task(
            user_message=user_message,
            session_state=session_state,
            session_tag=session_tag,
        )

    def _handle_research_task(
        self,
        *,
        user_message: str,
        original_user_message: str | None = None,
        session_state: Dict[str, Any] | None = None,
        session_tag: str = "session",
        route: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Route exploratory tasks through ResearchLoop.

        Requires self.research_loop to be configured. The ResearchLoop must already
        know the input h5ad path (set at construction time). The session_state is
        passed as context but the ResearchLoop owns its own data profiling.
        """
        session_state = dict(session_state or {})
        intent_mode = (route or {}).get("intent_mode", "discovery")
        pipeline_mode_map = {
            "discovery": "full",
            "ambiguous": "brief",
        }
        pipeline_mode = pipeline_mode_map.get(intent_mode)
        if pipeline_mode is None:
            return {
                "decision": {
                    "route": "research_loop",
                    "intent_mode": intent_mode,
                    "execution_path": "research_loop",
                },
                "raw_results": {
                    "research_loop_result": {
                        "status": "failed",
                        "error": f"Unsupported research intent_mode: {intent_mode}",
                    }
                },
                "result": {
                    "status": "failed",
                    "message": f"Unsupported research intent_mode: {intent_mode}",
                    "images": [],
                    "execution_path": "research_loop",
                },
            }

        if self.research_loop is None:
            message = (
                "This request was classified as exploratory/discovery, but ResearchLoop is not configured "
                "for this session. Configure ResearchLoop or rephrase the request as a concrete operational workflow."
            )
            return {
                "decision": {
                    "route": "research_loop_unavailable",
                    "intent_mode": intent_mode,
                    "pipeline_mode": pipeline_mode,
                    "execution_path": "research_loop",
                },
                "raw_results": {
                    "research_loop_result": {
                        "status": "failed",
                        "error": message,
                    }
                },
                "result": {
                    "status": "failed",
                    "message": message,
                    "images": [],
                    "execution_path": "research_loop",
                    "pipeline_mode": pipeline_mode,
                },
            }

        workspace_decision: dict[str, Any] | None = None
        research_state = None
        if self.research_workspace is not None:
            resolution = self.research_workspace.resolve_research_state(
                user_message=original_user_message or user_message,
                resolved_intent=user_message,
                data_summary=getattr(self.research_loop, "data_summary", {}),
                session_context=session_state,
            )
            research_state = resolution.research_state
            workspace_decision = resolution.decision

        try:
            loop_result = _call_research_loop(
                self.research_loop,
                user_question=user_message,
                original_user_message=original_user_message or user_message,
                session_context=session_state,
                research_state=research_state,
                workspace_decision=workspace_decision,
                pipeline_mode=pipeline_mode,
            )
        except Exception as exc:
            loop_result = {"status": "failed", "error": str(exc), "phases_completed": 0}

        loop_status = str(loop_result.get("status", "failed"))
        final_report = loop_result.get("final_report") or {}
        message = (
            final_report.get("summary")
            or final_report.get("conclusion")
            or final_report.get("message")
            or (
                f"Research loop completed: {loop_status} "
                f"after {loop_result.get('phases_completed', 0)} phase(s)."
            )
        )
        status = _frontend_research_status(loop_status)
        figures = _collect_images_from_raw_results({"research_loop_result": loop_result})

        payload = {
            "decision": {
                "route": "research_loop",
                "intent_mode": intent_mode,
                "pipeline_mode": pipeline_mode,
                "execution_path": "research_loop",
            },
            "raw_results": {"research_loop_result": loop_result},
            "result": {
                "status": status,
                "message": message,
                "figures": figures,
                "images": figures,
                "execution_path": "research_loop",
                "pipeline_mode": pipeline_mode,
                "loop_status": loop_status,
                "workspace_decision": workspace_decision,
                "raw_results": {"research_loop_result": loop_result},
            },
        }
        out_path = self.feedback_dir / f"{session_tag}_research_task.json"
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        payload["research_task_path"] = str(out_path)
        return payload

    def execute_task(
        self,
        *,
        user_message: str,
        session_state: Dict[str, Any] | None = None,
        session_tag: str = "session",
        allow_research: bool = False,
    ) -> Dict[str, Any]:
        session_state = dict(session_state or {})
        decision = self.tool_consultant.decide(
            user_message=user_message,
            session_state=session_state,
            session_tag=f"{session_tag}_tool_consultant",
        )
        if not _is_composable_decision(decision):
            raise ValueError("ToolConsultant returned a legacy task decision; expected composable plan fields.")
        payload = self._execute_composable_task(
            user_message=user_message,
            session_state=session_state,
            session_tag=session_tag,
            decision=decision,
            allow_research=allow_research or bool(decision.get("research_brief")),
        )
        out_path = self.feedback_dir / f"{session_tag}_task_execution.json"
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        payload["task_execution_path"] = str(out_path)
        return payload

    def _execute_composable_task(
        self,
        *,
        user_message: str,
        session_state: Dict[str, Any],
        session_tag: str,
        decision: Dict[str, Any],
        allow_research: bool,
    ) -> Dict[str, Any]:
        raw_results: dict[str, Any] = {}
        if decision.get("research_brief"):
            if self.research_executor is None:
                raw_results["research_result"] = {
                    "status": "failed",
                    "error": "Research pipeline is not configured for this session.",
                }
            elif not allow_research:
                raw_results["research_result"] = {
                    "status": "failed",
                    "error": "Research execution is not allowed for this task call.",
                }
            else:
                raw_results["research_result"] = self.research_executor.execute(
                    user_message=user_message,
                    session_state=session_state,
                    session_tag=f"{session_tag}_research",
                )
            return self._build_composable_payload(
                user_message=user_message,
                decision=decision,
                raw_results=raw_results,
                session_tag=session_tag,
            )

        if decision.get("dag_plan"):
            if self.dag_executor is None:
                raw_results["dag_result"] = {"status": "failed", "error": "DAG executor is not configured."}
            else:
                raw_results["dag_result"] = self.dag_executor.execute(
                    dag_plan=decision["dag_plan"],
                    session_tag=f"{session_tag}_dag",
                )
            if raw_results["dag_result"].get("status") == "failed" and _coder_depends_on_dag(decision):
                return self._build_composable_payload(
                    user_message=user_message,
                    decision=decision,
                    raw_results=raw_results,
                    session_tag=session_tag,
                )

        if decision.get("implementation_plan"):
            impl_plan = copy.deepcopy(decision["implementation_plan"])
            if impl_plan.get("depends_on_dag"):
                dag_result = raw_results.get("dag_result") or {}
                best_path = dag_result.get("best_path")
                if not isinstance(best_path, dict):
                    raw_results["coder_result"] = {
                        "status": "failed",
                        "error": "implementation_plan depends_on_dag=true but no DAG best_path is available.",
                    }
                    return self._build_composable_payload(
                        user_message=user_message,
                        decision=decision,
                        raw_results=raw_results,
                        session_tag=session_tag,
                    )
                try:
                    impl_plan = _resolve_dag_inputs(impl_plan, best_path)
                    impl_plan["depends_on_dag"] = False  # resolved; prevent re-validation failure in coder
                except Exception as exc:
                    raw_results["coder_result"] = {"status": "failed", "error": str(exc)}
                    return self._build_composable_payload(
                        user_message=user_message,
                        decision=decision,
                        raw_results=raw_results,
                        session_tag=session_tag,
                    )
            # Resolve session_output.* references from prior-turn state
            if _has_session_output_reference((impl_plan.get("inputs") or {}).values()):
                try:
                    impl_plan = _resolve_session_inputs(impl_plan, self.state_store.snapshot())
                except Exception as exc:
                    raw_results["coder_result"] = {"status": "failed", "error": str(exc)}
                    return self._build_composable_payload(
                        user_message=user_message,
                        decision=decision,
                        raw_results=raw_results,
                        session_tag=session_tag,
                    )
            coder_session = dict(session_state)
            coder_session.update(impl_plan.get("inputs") or {})
            raw_results["coder_result"] = self.coder.run(
                implementation_plan=impl_plan,
                session_state=coder_session,
                session_tag=f"{session_tag}_coder",
            )

        return self._build_composable_payload(
            user_message=user_message,
            decision=decision,
            raw_results=raw_results,
            session_tag=session_tag,
        )

    def _build_composable_payload(
        self,
        *,
        user_message: str,
        decision: Dict[str, Any],
        raw_results: Dict[str, Any],
        session_tag: str,
    ) -> Dict[str, Any]:
        status = _overall_status(raw_results)
        if self.result_summarizer is not None:
            summary = self.result_summarizer.summarize(
                user_query=user_message,
                decision=decision,
                raw_results=raw_results,
                session_tag=f"{session_tag}_result_summarizer",
            )
            message = summary.get("message", "")
            figures = summary.get("figures", [])
        else:
            message = _fallback_composable_message(raw_results)
            figures = _collect_images_from_raw_results(raw_results)
        return {
            "decision": decision,
            "raw_results": raw_results,
            "result": {
                "status": status,
                "message": message,
                "figures": figures,
                "images": figures,
                "execution_path": "tool_execution",
                "raw_results": raw_results,
            },
            "tool_artifact_dir": str(self.tool_artifact_dir),
        }

    def _build_task_session_state(self, session_state: Dict[str, Any]) -> Dict[str, Any]:
        planning_state = dict(session_state)
        persistent = self.state_store.snapshot()
        persistent.pop("history", None)
        previous_plan_type, previous_plan = _extract_previous_plan(persistent)
        planning_state["persistent_session"] = persistent
        planning_state["execution_context"] = _build_execution_context(planning_state, persistent)
        planning_state["previous_plan_type"] = previous_plan_type
        planning_state["previous_plan"] = previous_plan
        planning_state["previous_result_summary"] = _build_previous_result_summary(persistent)
        return planning_state


class DeterministicResponder:
    """Deterministic direct-response handler for session/artifact answers."""

    def __init__(self, state_store: SessionStateStore):
        self.state_store = state_store

    def respond(self, route: Dict[str, Any]) -> Dict[str, Any]:
        artifact_payload = self._artifact_lookup_response(route)
        if artifact_payload is not None:
            return artifact_payload
        response = route.get("response") or self._answer_from_session(route)
        return {
            "decision": {},
            "result": {
                "status": "completed",
                "message": response,
                "images": [],
                "source": "deterministic_responder",
                "execution_path": "direct_response",
            },
        }

    def _artifact_lookup_response(self, route: Dict[str, Any]) -> Dict[str, Any] | None:
        if not route.get("requires_artifact_lookup"):
            return None
        path = _resolve_referenced_artifact(route, self.state_store.snapshot())
        if path is None:
            return None
        try:
            content = _read_artifact_for_display(path)
        except Exception as exc:
            return _message("failed", f"Could not read artifact {path}: {exc}")
        return {
            "decision": {
                "decision": "artifact_lookup",
                "task": "Read existing artifact",
                "artifact_path": str(path),
                "reason": route.get("reason", ""),
            },
            "result": {
                "status": "completed",
                "message": content["text"],
                "images": content["images"],
                "artifact_path": str(path),
                "source": "artifact_lookup",
                "execution_path": "direct_response",
            },
        }

    def _answer_from_session(self, route: Dict[str, Any]) -> str:
        state = self.state_store.snapshot()
        lines: list[str] = []
        resolved_intent = str(route.get("resolved_intent") or "").strip()
        if resolved_intent and route.get("response") is None:
            lines.append(f"Request: {resolved_intent}")
        decision = state.get("last_decision") if isinstance(state.get("last_decision"), dict) else {}
        result = state.get("last_result") if isinstance(state.get("last_result"), dict) else {}
        if result:
            lines.append(_summarize_result(result))
        artifact_summaries = _summarize_execution_artifacts(state)
        if artifact_summaries:
            lines.extend(artifact_summaries)
        if not lines:
            return "I do not see prior session artifacts or results that answer that yet."
        return "\n\n".join(line for line in lines if line)


def _message(status: str, message: str) -> Dict[str, Any]:
    return {"decision": {}, "result": {"status": status, "message": message, "execution_path": "direct_response"}}


def _extract_previous_plan(persistent: Dict[str, Any]) -> tuple[str, str]:
    decision = persistent.get("last_decision") if isinstance(persistent.get("last_decision"), dict) else {}
    if any(key in decision for key in ("dag_plan", "implementation_plan", "research_brief")):
        slim = {
            key: decision.get(key)
            for key in ("dag_plan", "implementation_plan", "research_brief")
            if decision.get(key) is not None
        }
        if slim:
            return "composable", json.dumps(slim, indent=2, ensure_ascii=False)
    return "none", "<none>"


def _build_execution_context(session_state: Dict[str, Any], persistent: Dict[str, Any]) -> Dict[str, Any]:
    context: Dict[str, Any] = {}
    for key in ("input_h5ad_path", "input_mod2_path", "tool_artifact_dir", "initial_query"):
        value = session_state.get(key)
        if value:
            context[key] = value
    for key in ("active_h5ad_path", "active_cluster_key", "active_embedding_key"):
        value = persistent.get(key)
        if value:
            context[key] = value
    artifacts = persistent.get("last_artifacts") if isinstance(persistent.get("last_artifacts"), dict) else {}
    if artifacts:
        context["last_artifacts"] = artifacts
    return context


def _build_previous_result_summary(persistent: Dict[str, Any]) -> str:
    result = persistent.get("last_result") if isinstance(persistent.get("last_result"), dict) else {}
    if result:
        return _summarize_result(_trim_last_result(result))
    return "<none>"


def _trim_persistent_session(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    trimmed = copy.deepcopy(snapshot)
    trimmed.pop("history", None)
    decision = trimmed.get("last_decision")
    if isinstance(decision, dict):
        slim_decision = {
            key: decision[key]
            for key in ("decision", "task", "objective_name")
            if decision.get(key) is not None
        }
        trimmed["last_decision"] = slim_decision
    result = trimmed.get("last_result")
    if isinstance(result, dict):
        trimmed["last_result"] = _trim_last_result(result)
    route = trimmed.get("last_route")
    if isinstance(route, dict):
        trimmed["last_route"] = {
            key: route[key]
            for key in ("route", "reason")
            if route.get(key) is not None
        }
    return trimmed


def _trim_last_result(result: Dict[str, Any]) -> Dict[str, Any]:
    keep = (
        "status",
        "message",
        "search_summary",
        "recommendation",
        "error",
        "objective_name",
        "artifact_dir",
        "artifact_path",
        "overview_path",
        "report_path",
        "trace_path",
        "script_path",
        "output_h5ad_path",
    )
    trimmed = {key: result[key] for key in keep if result.get(key) is not None}
    tool_calls = result.get("tool_calls_used")
    if isinstance(tool_calls, list) and tool_calls:
        trimmed["tool_calls_used"] = [str(item) for item in tool_calls[:8]]
    nested = result.get("last_result")
    if isinstance(nested, dict):
        nested_keep = (
            "status",
            "message",
            "error",
            "output_h5ad_path",
            "plot_path",
            "figure_path",
        )
        nested_trimmed = {key: nested[key] for key in nested_keep if nested.get(key) is not None}
        if nested_trimmed:
            trimmed["last_result"] = nested_trimmed
    return trimmed


def _resolve_referenced_artifact(route: Dict[str, Any], state: Dict[str, Any]) -> Path | None:
    candidates: list[Path] = []
    haystack_parts = [
        str(route.get("resolved_intent") or ""),
        str(route.get("reason") or ""),
    ]
    for text in haystack_parts:
        candidates.extend(_extract_paths(text))

    artifacts = state.get("last_artifacts") if isinstance(state.get("last_artifacts"), dict) else {}
    for value in artifacts.values():
        if isinstance(value, str):
            candidates.append(Path(value))

    result = state.get("last_result") if isinstance(state.get("last_result"), dict) else {}
    for key in ("artifact_path", "overview_path", "report_path", "trace_path", "script_path"):
        if isinstance(result.get(key), str):
            candidates.append(Path(result[key]))
    nested = result.get("artifacts") if isinstance(result.get("artifacts"), dict) else {}
    for value in nested.values():
        if isinstance(value, str):
            candidates.append(Path(value))

    instructions = " ".join(haystack_parts).lower()
    existing = [path.expanduser() for path in candidates if path.expanduser().is_file()]
    if not existing:
        return None
    if instructions:
        named = [
            path
            for path in existing
            if path.name.lower() in instructions or str(path).lower() in instructions
        ]
        if named:
            return named[0]
    return existing[0]


def _extract_paths(text: str) -> list[Path]:
    if not text:
        return []
    pattern = r"(?:~|/|\.{1,2}/)[^\s\"'<>]+"
    paths: list[Path] = []
    for match in re.finditer(pattern, text):
        raw = match.group(0).rstrip(".,);]")
        if raw:
            paths.append(Path(raw))
    return paths


_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
_BINARY_SUFFIXES = _IMAGE_SUFFIXES | {".svg", ".h5ad", ".h5", ".hdf5", ".pkl", ".pickle", ".npy", ".npz", ".pdf"}


def _read_artifact_for_display(path: Path, *, max_bytes: int = 200_000) -> Dict[str, Any]:
    suffix = path.suffix.lower()
    size = path.stat().st_size
    if suffix in _IMAGE_SUFFIXES:
        return {"text": f"Image: {path.name}", "images": [str(path)]}
    if suffix in _BINARY_SUFFIXES:
        return {"text": f"Binary file ({suffix or 'unknown'}, {size:,} bytes): {path}", "images": []}
    if size > max_bytes:
        raise ValueError(f"file is too large to display directly ({size} bytes)")
    text = path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".json":
        payload = json.loads(text)
        text = json.dumps(payload, indent=2, ensure_ascii=False)
    return {"text": text.strip() or f"{path} is empty.", "images": []}


def _summarize_result(result: Dict[str, Any]) -> str:
    keys = ["status", "message", "artifact_dir", "trace_path", "report_path"]
    lines = ["Previous result:"]
    for key in keys:
        if result.get(key):
            lines.append(f"- {key}: {result[key]}")
    return "\n".join(lines)


def _summarize_execution_artifacts(state: Dict[str, Any]) -> list[str]:
    summaries: list[str] = []
    seen: set[Path] = set()
    artifacts = state.get("last_artifacts") if isinstance(state.get("last_artifacts"), dict) else {}
    result = state.get("last_result") if isinstance(state.get("last_result"), dict) else {}
    candidate_paths: list[str] = []
    for source in (artifacts, result):
        for key in ("trace_path", "report_path"):
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                candidate_paths.append(value)

    for raw_path in candidate_paths:
        path = Path(raw_path).expanduser()
        try:
            resolved = path.resolve()
        except Exception:
            continue
        if resolved in seen or not resolved.is_file():
            continue
        seen.add(resolved)
        payload = _load_json_summary_payload(resolved)
        if payload is None:
            continue
        summary = _summarize_loaded_execution_payload(resolved, payload)
        if summary:
            summaries.append(summary)
    return summaries


def _load_json_summary_payload(path: Path, *, max_bytes: int = 400_000) -> Any | None:
    try:
        size = path.stat().st_size
    except OSError:
        return None
    if size > max_bytes:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _summarize_loaded_execution_payload(path: Path, payload: Any) -> str:
    if isinstance(payload, list):
        return _summarize_tool_trace(path, payload)
    if isinstance(payload, dict):
        if "attempt_log" in payload:
            return _summarize_coder_report(path, payload)
        if "best_trial" in payload or "trials_run" in payload or "failed_trials" in payload:
            return _summarize_optimizer_report(path, payload)
        return _summarize_generic_report(path, payload)
    return ""


def _summarize_tool_trace(path: Path, trace: list[Any]) -> str:
    lines = [f"Execution trace details ({path.name}):", f"- steps: {len(trace)}"]
    for item in trace[:5]:
        if not isinstance(item, dict):
            continue
        tool_name = str(item.get("tool_name") or item.get("tool") or "unknown").strip()
        result = item.get("result") if isinstance(item.get("result"), dict) else {}
        status = "error" if result.get("error") else str(result.get("status") or "completed").strip() or "completed"
        detail = ""
        if result.get("error"):
            detail = f" ({str(result['error']).strip()[:120]})"
        elif result.get("message"):
            detail = f" ({str(result['message']).strip()[:120]})"
        lines.append(f"- {tool_name}: {status}{detail}")
    return "\n".join(lines)


def _summarize_coder_report(path: Path, report: Dict[str, Any]) -> str:
    lines = [f"Coder report details ({path.name}):"]
    if report.get("status"):
        lines.append(f"- status: {report['status']}")
    if report.get("attempts") is not None:
        lines.append(f"- attempts: {report['attempts']}")
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    if metrics:
        lines.append(f"- metrics: {_compact_json(metrics)}")
    attempt_log = report.get("attempt_log") if isinstance(report.get("attempt_log"), list) else []
    if attempt_log:
        latest = attempt_log[-1] if isinstance(attempt_log[-1], dict) else {}
        execution = latest.get("execution_result") if isinstance(latest.get("execution_result"), dict) else {}
        if execution.get("returncode") is not None:
            lines.append(f"- last return code: {execution.get('returncode')}")
        if execution.get("stderr"):
            lines.append(f"- last stderr: {str(execution['stderr']).strip()[:160]}")
    return "\n".join(lines)


def _summarize_optimizer_report(path: Path, report: Dict[str, Any]) -> str:
    lines = [f"Optimization report details ({path.name}):"]
    if report.get("status"):
        lines.append(f"- status: {report['status']}")
    if report.get("trials_run") is not None:
        lines.append(f"- trials run: {report['trials_run']}")
    best_trial = report.get("best_trial") if isinstance(report.get("best_trial"), dict) else {}
    if best_trial:
        lines.append(f"- best trial: {_compact_json(best_trial)}")
    failed_trials = report.get("failed_trials") if isinstance(report.get("failed_trials"), list) else []
    if failed_trials:
        lines.append(f"- failed trials: {len(failed_trials)}")
    recommendation = str(report.get("recommendation") or "").strip()
    if recommendation:
        lines.append(f"- recommendation: {recommendation[:160]}")
    return "\n".join(lines)


def _summarize_generic_report(path: Path, payload: Dict[str, Any]) -> str:
    lines = [f"Artifact details ({path.name}):"]
    for key in ("status", "message", "summary", "error"):
        value = payload.get(key)
        if value:
            lines.append(f"- {key}: {str(value)[:160]}")
    if len(lines) == 1:
        keys = ", ".join(sorted(str(key) for key in payload.keys())[:8])
        lines.append(f"- keys: {keys or '<none>'}")
    return "\n".join(lines)


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _is_composable_decision(decision: Dict[str, Any]) -> bool:
    return "decision" not in decision


def _coder_depends_on_dag(decision: Dict[str, Any]) -> bool:
    impl_plan = decision.get("implementation_plan")
    return isinstance(impl_plan, dict) and bool(impl_plan.get("depends_on_dag"))


def _resolve_dag_inputs(implementation_plan: Dict[str, Any], best_path: Dict[str, Any]) -> Dict[str, Any]:
    resolved = copy.deepcopy(implementation_plan)
    inputs = dict(resolved.get("inputs") or {})
    artifacts = best_path.get("artifacts") if isinstance(best_path.get("artifacts"), dict) else {}
    outputs = best_path.get("resolved_outputs") if isinstance(best_path.get("resolved_outputs"), dict) else {}
    for key, value in list(inputs.items()):
        if value == "dag_output.path_dir":
            inputs[key] = best_path["path_dir"]
        elif value == "dag_output.artifacts":
            inputs[key] = artifacts
        elif isinstance(value, str) and value.startswith("dag_output.artifacts."):
            field = value[len("dag_output.artifacts."):]
            if field not in artifacts:
                raise ValueError(
                    f"implementation_plan.inputs['{key}'] references dag_output.artifacts.{field}, "
                    f"but available artifact keys are: {sorted(artifacts)}"
                )
            inputs[key] = artifacts[field]
        elif isinstance(value, str) and value.startswith("dag_output.resolved_outputs."):
            field = value[len("dag_output.resolved_outputs."):]
            if field not in outputs:
                raise ValueError(
                    f"implementation_plan.inputs['{key}'] references dag_output.resolved_outputs.{field}, "
                    f"but available resolved output keys are: {sorted(outputs)}"
                )
            inputs[key] = outputs[field]
    resolved["inputs"] = inputs
    # Also resolve dag_output.* substrings in outputs (e.g., "dag_output.path_dir/plot.png")
    resolved["outputs"] = _substitute_dag_refs_in_outputs(
        dict(resolved.get("outputs") or {}), best_path, artifacts, outputs,
    )
    return resolved


def _substitute_dag_refs_in_outputs(
    outputs: Dict[str, Any],
    best_path: Dict[str, Any],
    artifacts: Dict[str, Any],
    resolved_outputs: Dict[str, Any],
) -> Dict[str, Any]:
    """Resolve dag_output.* substrings inside implementation_plan.outputs values."""
    path_dir = str(best_path.get("path_dir") or "")
    result: Dict[str, Any] = {}
    for key, value in outputs.items():
        if not isinstance(value, str):
            result[key] = value
            continue
        text = value
        if "dag_output.path_dir" in text:
            text = text.replace("dag_output.path_dir", path_dir)
        for rk, rv in resolved_outputs.items():
            token = f"dag_output.resolved_outputs.{rk}"
            if token in text:
                text = text.replace(token, str(rv))
        for ak, av in artifacts.items():
            token = f"dag_output.artifacts.{ak}"
            if token in text and isinstance(av, str):
                text = text.replace(token, av)
        result[key] = text
    return result


def _substitute_session_refs_in_outputs(
    outputs: Dict[str, Any],
    session_snapshot: Dict[str, Any],
) -> Dict[str, Any]:
    """Resolve session_output.* substrings inside implementation_plan.outputs values."""
    artifacts = session_snapshot.get("last_artifacts") if isinstance(session_snapshot.get("last_artifacts"), dict) else {}
    replacements = {
        "session_output.active_h5ad_path": str(session_snapshot.get("active_h5ad_path") or ""),
        "session_output.active_embedding_key": str(session_snapshot.get("active_embedding_key") or ""),
        "session_output.active_cluster_key": str(session_snapshot.get("active_cluster_key") or ""),
        "session_output.path_dir": str(artifacts.get("path_dir") or ""),
    }
    for ak, av in artifacts.items():
        if isinstance(av, str):
            replacements[f"session_output.artifacts.{ak}"] = av
    result: Dict[str, Any] = {}
    for key, value in outputs.items():
        if not isinstance(value, str):
            result[key] = value
            continue
        text = value
        for token, replacement in replacements.items():
            if token in text:
                text = text.replace(token, replacement)
        result[key] = text
    return result


def _has_session_output_reference(values) -> bool:
    """Check if any input value uses session_output.* references."""
    for value in values:
        if isinstance(value, str) and value.startswith("session_output."):
            return True
    return False


def _resolve_session_inputs(implementation_plan: Dict[str, Any], session_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve session_output.* references in implementation_plan.inputs from prior-turn session state."""
    resolved = copy.deepcopy(implementation_plan)
    inputs = dict(resolved.get("inputs") or {})
    artifacts = session_snapshot.get("last_artifacts") if isinstance(session_snapshot.get("last_artifacts"), dict) else {}

    _ACTIVE_KEYS = {
        "session_output.active_h5ad_path": "active_h5ad_path",
        "session_output.active_embedding_key": "active_embedding_key",
        "session_output.active_cluster_key": "active_cluster_key",
    }

    for key, value in list(inputs.items()):
        if not isinstance(value, str) or not value.startswith("session_output."):
            continue
        if value in _ACTIVE_KEYS:
            resolved_value = session_snapshot.get(_ACTIVE_KEYS[value])
            if not resolved_value:
                raise ValueError(
                    f"implementation_plan.inputs['{key}'] references {value}, "
                    f"but {_ACTIVE_KEYS[value]} is not set in session state."
                )
            inputs[key] = resolved_value
        elif value == "session_output.artifacts":
            inputs[key] = artifacts
        elif value == "session_output.path_dir":
            path_dir = artifacts.get("path_dir")
            if not path_dir:
                raise ValueError(
                    f"implementation_plan.inputs['{key}'] references session_output.path_dir, "
                    "but no path_dir is available in last_artifacts."
                )
            inputs[key] = path_dir
        elif value.startswith("session_output.artifacts."):
            field = value[len("session_output.artifacts."):]
            if field not in artifacts:
                raise ValueError(
                    f"implementation_plan.inputs['{key}'] references session_output.artifacts.{field}, "
                    f"but available artifact keys are: {sorted(artifacts)}"
                )
            inputs[key] = artifacts[field]
        else:
            raise ValueError(
                f"implementation_plan.inputs['{key}'] has unrecognized session_output reference: {value}"
            )
    resolved["inputs"] = inputs
    # Also resolve session_output.* substrings in outputs
    resolved["outputs"] = _substitute_session_refs_in_outputs(
        dict(resolved.get("outputs") or {}), session_snapshot,
    )
    return resolved


def _overall_status(raw_results: Dict[str, Any]) -> str:
    if not raw_results:
        return "completed"
    statuses = []
    for result in raw_results.values():
        if isinstance(result, dict):
            statuses.append(str(result.get("status") or "completed"))
    if any(status == "failed" for status in statuses):
        return "failed"
    if any(status == "partial" for status in statuses):
        return "partial"
    return "completed"


def _frontend_research_status(loop_status: str) -> str:
    return {
        "done": "completed",
        "awaiting_user": "needs_input",
        "abstain": "not_answerable",
        "max_phases_reached": "partial",
        "failed": "failed",
    }.get(str(loop_status or "failed"), "failed")


def _call_research_loop(research_loop: Any, **kwargs: Any) -> dict[str, Any]:
    signature = inspect.signature(research_loop.run)
    accepted = {
        key: value
        for key, value in kwargs.items()
        if key in signature.parameters and value is not None
    }
    return research_loop.run(**accepted)


def _fallback_composable_message(raw_results: Dict[str, Any]) -> str:
    status = _overall_status(raw_results)
    parts = [f"Status: {status}."]
    dag_result = raw_results.get("dag_result") if isinstance(raw_results.get("dag_result"), dict) else {}
    if dag_result:
        best = dag_result.get("best_path") if isinstance(dag_result.get("best_path"), dict) else {}
        if best:
            parts.append(f"DAG best path: {best.get('path_index')}.")
            if best.get("metrics"):
                parts.append(f"Metrics: {_compact_json(best['metrics'])}.")
        elif dag_result.get("error"):
            parts.append(f"DAG error: {dag_result['error']}.")
    coder_result = raw_results.get("coder_result") if isinstance(raw_results.get("coder_result"), dict) else {}
    if coder_result:
        if coder_result.get("message"):
            parts.append(str(coder_result["message"]))
        elif coder_result.get("error"):
            parts.append(f"Coder error: {coder_result['error']}.")
    research_result = raw_results.get("research_result") if isinstance(raw_results.get("research_result"), dict) else {}
    if research_result:
        if research_result.get("message"):
            parts.append(str(research_result["message"]))
        elif research_result.get("error"):
            parts.append(f"Research error: {research_result['error']}.")
    return " ".join(parts)


def _collect_images_from_raw_results(raw_results: Dict[str, Any]) -> list[str]:
    image_suffixes = {".png", ".jpg", ".jpeg", ".svg", ".webp"}
    images: list[str] = []
    seen: set[str] = set()

    def walk(obj: Any) -> None:
        if isinstance(obj, str):
            path = Path(obj)
            if path.suffix.lower() in image_suffixes and path.exists():
                text = str(path)
                if text not in seen:
                    seen.add(text)
                    images.append(text)
        elif isinstance(obj, dict):
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for value in obj:
                walk(value)

    walk(raw_results)
    return images
