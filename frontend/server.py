from __future__ import annotations

import argparse
import html
import json
import mimetypes
import os
import re
import sys
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from agents.session_state import assistant_display_text


HTML_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Single-Cell Consultant</title>
  <style>
    :root {
      --ink: #1b1b18;
      --muted: #706b61;
      --paper: #f6f0e5;
      --panel: #fffaf1;
      --line: #d5c7ae;
      --accent: #1d6f5f;
      --accent-dark: #12463d;
      --danger: #a23d2a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
      background:
        radial-gradient(circle at 10% 10%, rgba(29,111,95,0.16), transparent 28rem),
        radial-gradient(circle at 90% 20%, rgba(172,116,48,0.18), transparent 24rem),
        linear-gradient(135deg, #efe2ca, var(--paper));
    }
    .shell {
      width: min(1540px, calc(100vw - 28px));
      margin: 0 auto;
      padding: 28px 0;
      display: grid;
      grid-template-columns: 300px minmax(420px, 1fr) 380px;
      gap: 18px;
    }
    .card {
      border: 1px solid var(--line);
      background: rgba(255,250,241,0.92);
      box-shadow: 0 18px 60px rgba(65,45,18,0.15);
      border-radius: 22px;
    }
    aside {
      padding: 22px;
      position: sticky;
      top: 18px;
      height: calc(100vh - 56px);
      overflow: auto;
    }
    h1 {
      margin: 0 0 8px;
      font-size: 30px;
      line-height: 1;
      letter-spacing: -0.04em;
    }
    .subtitle {
      color: var(--muted);
      font-size: 14px;
      line-height: 1.45;
      margin-bottom: 24px;
    }
    .meta {
      border-top: 1px solid var(--line);
      padding-top: 16px;
      display: grid;
      gap: 10px;
      font-size: 13px;
    }
    .meta b {
      display: block;
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 3px;
    }
    main {
      min-height: calc(100vh - 56px);
      display: grid;
      grid-template-rows: 1fr auto;
      overflow: hidden;
    }
    #messages {
      padding: 22px;
      overflow: auto;
      display: flex;
      flex-direction: column;
      gap: 14px;
      max-height: calc(100vh - 185px);
    }
    .msg {
      width: min(820px, 100%);
      padding: 15px 16px;
      border-radius: 18px;
      border: 1px solid var(--line);
      line-height: 1.45;
      white-space: pre-wrap;
    }
    .user {
      align-self: flex-end;
      background: #173f38;
      color: #fffaf1;
      border-color: #173f38;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 13px;
    }
    .assistant {
      align-self: flex-start;
      background: var(--panel);
    }
    .toolbox {
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px dashed var(--line);
      font-size: 13px;
      color: var(--muted);
    }
    .error {
      color: var(--danger);
      border-color: rgba(162,61,42,0.35);
    }
    .msg img {
      display: block;
      max-width: 100%;
      border-radius: 12px;
      margin-top: 10px;
      border: 1px solid var(--line);
      background: #fffdf8;
    }
    form {
      border-top: 1px solid var(--line);
      padding: 16px;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      background: rgba(255,250,241,0.84);
    }
    textarea {
      resize: vertical;
      min-height: 62px;
      max-height: 180px;
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px 15px;
      font: 15px/1.4 Georgia, "Times New Roman", serif;
      background: #fffdf8;
      color: var(--ink);
      outline: none;
    }
    textarea:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(29,111,95,0.13); }
    button {
      border: 0;
      border-radius: 18px;
      background: var(--accent);
      color: white;
      padding: 0 22px;
      font-weight: 700;
      cursor: pointer;
      min-width: 110px;
    }
    button:disabled {
      background: #8ca79f;
      cursor: wait;
    }
    code {
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
      background: rgba(0,0,0,0.05);
      padding: 2px 5px;
      border-radius: 5px;
    }
    .activity {
      padding: 18px;
      position: sticky;
      top: 18px;
      height: calc(100vh - 56px);
      display: grid;
      grid-template-rows: auto 1fr;
      overflow: hidden;
    }
    .activity h2 {
      margin: 0;
      font-size: 20px;
      line-height: 1.1;
    }
    .activity .subtitle {
      margin: 7px 0 14px;
      font-size: 13px;
    }
    .activity-list {
      overflow: auto;
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding-right: 2px;
    }
    .activity-item {
      border: 1px solid rgba(213,199,174,0.9);
      background: rgba(255,253,248,0.78);
      border-radius: 10px;
      padding: 10px 11px;
      font-size: 13px;
      line-height: 1.35;
    }
    .activity-item strong {
      display: block;
      font-size: 13px;
      margin-bottom: 4px;
    }
    .activity-item span {
      display: block;
      color: var(--muted);
      white-space: pre-wrap;
    }
    .activity-empty {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
      border: 1px dashed var(--line);
      border-radius: 10px;
      padding: 12px;
    }
    @media (max-width: 1180px) {
      .shell { grid-template-columns: 280px minmax(0, 1fr); }
      .activity {
        grid-column: 1 / -1;
        position: static;
        height: min(420px, 70vh);
      }
    }
    @media (max-width: 860px) {
      .shell { grid-template-columns: 1fr; }
      aside, .activity { position: static; height: auto; }
      form { grid-template-columns: 1fr; }
      button { min-height: 48px; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <aside class="card">
      <h1>Single-Cell Consultant</h1>
      <div class="subtitle">Start by typing the analysis task. The first message becomes the session task; follow-up messages reuse that context.</div>
      <div class="meta">
        <div><b>Input</b><span id="inputPath"></span></div>
        <div><b>Engine</b><span id="engineName"></span></div>
        <div><b>Results</b><code id="resultsDir"></code></div>
        <div><b>Tool Artifacts</b><code id="toolArtifactDir"></code></div>
        <div><b>Tip</b>Start with the task, for example: “Run an RNA PCA preprocessing and clustering workflow, then report ARI/NMI.”</div>
      </div>
    </aside>
    <main class="card">
      <div id="messages"></div>
      <form id="chatForm">
        <textarea id="messageInput" placeholder="Describe the initial task, then ask follow-up questions..." required></textarea>
        <button id="sendButton" type="submit">Send</button>
      </form>
    </main>
    <section class="card activity" aria-label="System progress">
      <div>
        <h2>System Progress</h2>
        <div class="subtitle">Live rolling view of panel reasoning, paper retrieval, plans, and execution.</div>
      </div>
      <div id="activityList" class="activity-list">
        <div class="activity-empty">No active run yet.</div>
      </div>
    </section>
  </div>
  <script>
    const messages = document.getElementById("messages");
    const activityList = document.getElementById("activityList");
    const form = document.getElementById("chatForm");
    const input = document.getElementById("messageInput");
    const button = document.getElementById("sendButton");
    let progressTimer = null;

    function addMessage(role, text, extra = null, isError = false, images = []) {
      const node = document.createElement("div");
      node.className = `msg ${role} ${isError ? "error" : ""}`;
      node.textContent = text;
      if (images && images.length) {
        for (const src of images) {
          const img = document.createElement("img");
          img.src = src;
          const parts = String(src).split("/");
          img.alt = decodeURIComponent(parts[parts.length - 1] || "artifact image");
          img.onerror = () => {
            img.alt = "Could not load: " + img.alt;
            img.style.display = "none";
          };
          node.appendChild(img);
        }
      }
      if (extra) {
        const box = document.createElement("div");
        box.className = "toolbox";
        box.innerHTML = extra;
        node.appendChild(box);
      }
      messages.appendChild(node);
      messages.scrollTop = messages.scrollHeight;
    }

    function renderProgress(events) {
      activityList.innerHTML = "";
      if (!events || !events.length) {
        const empty = document.createElement("div");
        empty.className = "activity-empty";
        empty.textContent = "Waiting for the next run.";
        activityList.appendChild(empty);
        return;
      }
      for (const event of events.slice(-40)) {
        const item = document.createElement("div");
        item.className = "activity-item";
        const title = document.createElement("strong");
        title.textContent = event.title || "Progress update";
        const detail = document.createElement("span");
        detail.textContent = event.detail || "";
        item.appendChild(title);
        item.appendChild(detail);
        activityList.appendChild(item);
      }
      activityList.scrollTop = activityList.scrollHeight;
    }

    async function pollProgress() {
      try {
        const res = await fetch("/progress");
        if (!res.ok) return;
        const data = await res.json();
        renderProgress(data.events || []);
      } catch (_) {
        // Progress is best-effort; final chat result remains authoritative.
      }
    }

    function startProgressPolling() {
      if (progressTimer) clearInterval(progressTimer);
      pollProgress();
      progressTimer = setInterval(pollProgress, 1200);
    }

    function stopProgressPolling() {
      pollProgress();
      if (progressTimer) clearInterval(progressTimer);
      progressTimer = null;
    }

    async function loadStatus() {
      const res = await fetch("/status");
      const data = await res.json();
      document.getElementById("inputPath").textContent = data.input_h5ad_path;
      document.getElementById("engineName").textContent = data.engine;
      document.getElementById("resultsDir").textContent = data.result_dir;
      document.getElementById("toolArtifactDir").textContent = data.tool_artifact_dir;
      addMessage("assistant", "Frontend ready. Send the initial task. Follow-up messages will reuse the same session context.");
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const text = input.value.trim();
      if (!text) return;
      input.value = "";
      addMessage("user", text);
      button.disabled = true;
      button.textContent = "Running";
      startProgressPolling();
      try {
        const res = await fetch("/chat", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({message: text}),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Request failed");
        const route = data.route || {};
        const decision = data.decision || {};
        const result = data.result || {};
        const tools = (result.tool_calls_used || []).map(t => `<code>${t}</code>`).join(" ");
        const executionPath = result.execution_path || decision.execution_path || "unknown";
        const pipelineMode = result.pipeline_mode || decision.pipeline_mode || "n/a";
        const extra = `route: <code>${route.route || "unknown"}</code><br>intent: <code>${route.intent_mode || "unknown"}</code><br>execution: <code>${executionPath}</code><br>pipeline: <code>${pipelineMode}</code><br>decision: <code>${decision.decision || decision.route || "none"}</code><br>status: <code>${result.status || "unknown"}</code><br>tools: ${tools || "<code>none</code>"}<br>session: <code>${data.session_tag}</code>`;
        addMessage("assistant", result.search_summary || result.recommendation || result.message || JSON.stringify(data, null, 2), extra, false, result.images || []);
      } catch (err) {
        addMessage("assistant", String(err.message || err), null, true);
      } finally {
        button.disabled = false;
        button.textContent = "Send";
        stopProgressPolling();
        input.focus();
      }
    });

    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
        form.requestSubmit();
      }
    });

    loadStatus();
    pollProgress();
  </script>
</body>
</html>
"""


class _FrontendState:
    def __init__(self, *, args: argparse.Namespace):
        import textgrad as tg

        from agents.coder import CoderAgent
        from agents.dag_executor import DagExecutor
        from agents.analyzer_panel import AnalyzerPanel
        from agents.research_executor import SubprocessResearchExecutor
        from agents.research_loop import ResearchLoop
        from agents.research_workspace import ResearchWorkspace
        from agents.result_summarizer import ResultSummarizer
        from agents.scientist_panel import ScientistPanel
        from agents.short_term_memory import ShortTermMemory
        from agents.session_dispatcher import SessionDispatcher
        from agents.session_router import SessionRouter
        from agents.session_state import SessionStateStore
        from agents.tool_consultant import ToolConsultantAgent
        from backend import BackendConfig, SingleCellBackend
        from pipelines.config import Config
        from rag.store_backend import RAGStore

        self.args = args
        self.repo_root = Path(__file__).resolve().parents[1]
        self.turn = 0
        self.lock = threading.Lock()
        self.progress_lock = threading.Lock()
        self.active_session_tag: str | None = None
        self.active_run_started_at: float | None = None
        self.active_run_running = False

        tg.set_backward_engine(tg.get_engine(args.engine), override=True)
        self.config = Config(
            opt_step=1,
            max_fix_step=1,
            timeout=args.time_budget,
            mod1_path=args.input_mod1,
            mod2_path=args.input_mod2,
            metrics="combined_score",
            label_column=None,
            id_column=None,
            code_dir=args.code_dir,
            result_dir=args.results_dir,
            engine_name=args.engine,
        )
        self.config.api_dir = str(self.repo_root / "apis")
        self.config.dataset_dir = args.dataset_dir or str(self.repo_root / "Datasets")
        self.config.prior_resource_summary = self.config.summarize_prior_resources()
        Path(self.config.result_dir, "feedback").mkdir(parents=True, exist_ok=True)
        self.tool_artifact_dir = (
            _resolve_repo_path(self.repo_root, args.tool_artifact_dir)
            if args.tool_artifact_dir
            else Path(self.config.result_dir) / "tool_artifacts"
        )
        self.tool_artifact_dir.mkdir(parents=True, exist_ok=True)
        self.session_store = SessionStateStore(Path(self.config.result_dir) / "session_state.json")
        self.session_store.reset()

        self.backend = SingleCellBackend(
            BackendConfig(
                cache_dir=self.tool_artifact_dir / "backend_cache",
                scratch_dir=Path(self.config.result_dir) / "backend_scratch",
                log_dir=Path(self.config.result_dir) / "backend_logs",
                reticulate_python=Path(args.reticulate_python) if args.reticulate_python else Path(sys.executable),
            )
        )
        self.backend.bind_runtime_context(self.config)
        self.tool_consultant = ToolConsultantAgent(
            engine_name=args.engine,
            result_dir=self.config.result_dir,
            backend=self.backend,
        )
        self.dag_executor = DagExecutor(
            backend=self.backend,
            result_dir=self.tool_artifact_dir / "dag",
        )
        self.coder = CoderAgent(
            engine_name=args.engine,
            result_dir=self.config.result_dir,
            artifact_dir=self.tool_artifact_dir / "coder",
        )
        self.result_summarizer = ResultSummarizer(
            engine_name=args.engine,
            result_dir=self.config.result_dir,
        )
        self.research_loop_error: str | None = None
        self.research_loop = None
        try:
            rag_root = _resolve_repo_path(self.repo_root, args.rag_root)
            rag_store = RAGStore(
                root_dir=rag_root,
                embedding_backend=args.embedding_backend,
                embedding_model=args.embedding_model,
            )
            fast_engine = args.fast_engine or args.engine
            scientist_panel = ScientistPanel(
                engine_name=args.engine,
                fast_engine_name=fast_engine,
                rag_store=rag_store,
                result_dir=Path(self.config.result_dir) / "research_loop" / "scientist",
            )
            analyzer_panel = AnalyzerPanel(
                engine_name=args.engine,
                fast_engine_name=fast_engine,
                rag_store=rag_store,
                result_dir=Path(self.config.result_dir) / "research_loop" / "analyzer",
            )
            short_term_memory = ShortTermMemory(
                session_id="frontend",
                result_dir=Path(self.config.result_dir) / "research_loop" / "memory",
            )
            research_workspace = ResearchWorkspace(
                root_dir=Path(self.config.result_dir) / "research_loop" / "runs",
                conversation_id="C001",
            )
            self.research_loop = ResearchLoop(
                scientist_panel=scientist_panel,
                analyzer_panel=analyzer_panel,
                tool_consultant=self.tool_consultant,
                alignment_reviewer=scientist_panel.adversarial_panelist,
                dag_executor=self.dag_executor,
                coder=self.coder,
                short_term_memory=short_term_memory,
                input_h5ad_path=args.input_mod1,
                data_paths=[args.input_mod2] if args.input_mod2 else None,
                result_dir=Path(self.config.result_dir) / "research_loop",
                max_phases=args.research_max_phases,
                adversarial_panelist=scientist_panel.adversarial_panelist,
            )
            self.research_workspace = research_workspace
        except Exception as exc:
            self.research_loop_error = str(exc)
            self.research_workspace = None
        self.research_executor = SubprocessResearchExecutor(
            repo_root=self.repo_root,
            engine_name=args.engine,
            input_mod1=args.input_mod1,
            input_mod2=args.input_mod2,
            dataset_dir=self.config.dataset_dir,
            time_budget=args.time_budget,
            base_artifact_dir=self.tool_artifact_dir,
        )
        self.session_router = SessionRouter(
            engine_name=args.engine,
            result_dir=self.config.result_dir,
        )
        self.session_dispatcher = SessionDispatcher(
            router=self.session_router,
            tool_consultant=self.tool_consultant,
            coder=self.coder,
            research_executor=self.research_executor,
            tool_artifact_dir=self.tool_artifact_dir,
            state_store=self.session_store,
            result_dir=self.config.result_dir,
            dag_executor=self.dag_executor,
            result_summarizer=self.result_summarizer,
            research_loop=self.research_loop,
            research_workspace=getattr(self, "research_workspace", None),
        )

    def status(self) -> dict[str, Any]:
        return {
            "engine": self.args.engine,
            "input_h5ad_path": self.args.input_mod1,
            "result_dir": self.config.result_dir,
            "tool_artifact_dir": str(self.tool_artifact_dir),
            "initial_query": self.session_store.snapshot().get("initial_query"),
            "research_loop_configured": self.research_loop is not None,
            "research_loop_error": self.research_loop_error,
        }

    def progress(self) -> dict[str, Any]:
        with self.progress_lock:
            session_tag = self.active_session_tag
            started_at = self.active_run_started_at
            running = self.active_run_running
        if not session_tag:
            snapshot = self.session_store.snapshot()
            current = snapshot.get("current_turn") if isinstance(snapshot.get("current_turn"), dict) else {}
            session_tag = str(current.get("session_tag") or "").strip() or f"frontend_consultant_{self.turn:03d}"
        events = _collect_progress_events(
            result_dir=Path(self.config.result_dir),
            tool_artifact_dir=self.tool_artifact_dir,
            session_tag=session_tag,
            running=running,
            started_at=started_at,
            session_snapshot=self.session_store.snapshot(),
        )
        return {"session_tag": session_tag, "running": running, "events": events[-40:]}

    def chat(self, message: str) -> dict[str, Any]:
        clean_message = str(message or "").strip()
        if not clean_message:
            raise ValueError("message must be non-empty")
        with self.lock:
            self.turn += 1
            session_tag = f"frontend_consultant_{self.turn:03d}"
            with self.progress_lock:
                self.active_session_tag = session_tag
                self.active_run_started_at = time.time()
                self.active_run_running = True
            self.session_store.set_initial_query(clean_message)
            persistent = self.session_store.snapshot()
            session_state = {
                "input_h5ad_path": self.args.input_mod1,
                "input_mod2_path": self.args.input_mod2,
                "tool_artifact_dir": str(self.tool_artifact_dir),
                "initial_query": persistent.get("initial_query"),
                "current_message": clean_message,
                "history": self.session_store.history(limit=8),
            }
            self.session_store.begin_turn(user_message=clean_message, session_tag=session_tag)
            try:
                result = self.session_dispatcher.handle(
                    user_message=clean_message,
                    session_state=session_state,
                    session_tag=session_tag,
                )
            except Exception as exc:
                self.session_store.record_error(user_message=clean_message, error=str(exc))
                with self.progress_lock:
                    self.active_run_running = False
                raise
            payload_result = result.get("result") if isinstance(result.get("result"), dict) else {}
            images = payload_result.get("images") if isinstance(payload_result.get("images"), list) else []
            if images:
                payload_result["images"] = [
                    _artifact_url_for_path(
                        image_path,
                        tool_artifact_dir=self.tool_artifact_dir,
                        result_dir=Path(self.config.result_dir),
                    )
                    for image_path in images
                ]
            if payload_result and not any(payload_result.get(key) for key in ("message", "search_summary", "recommendation")):
                payload_result["message"] = assistant_display_text(result)
                if payload_result["message"].startswith("Error:") or payload_result["message"].startswith("Error reported"):
                    payload_result["status"] = "failed"
            self.session_store.record_turn(user_message=clean_message, payload=result)
            result["session_tag"] = session_tag
            with self.progress_lock:
                self.active_run_running = False
            return result


def _collect_progress_events(
    *,
    result_dir: Path,
    tool_artifact_dir: Path,
    session_tag: str,
    running: bool,
    started_at: float | None,
    session_snapshot: dict[str, Any],
) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    current_turn = session_snapshot.get("current_turn") if isinstance(session_snapshot.get("current_turn"), dict) else {}
    current_message = str(current_turn.get("user_message") or session_snapshot.get("initial_query") or "").strip()
    status = "running" if running else str(current_turn.get("status") or "idle")
    elapsed = int(time.time() - started_at) if started_at else 0
    if session_tag:
        detail = f"Session {session_tag}"
        if current_message:
            detail += f"\nTask: {_short(current_message, 160)}"
        if running:
            detail += f"\nElapsed: {elapsed}s"
        events.append(_event("Run status", f"{status.capitalize()}\n{detail}"))

    feedback_dir = result_dir / "feedback"
    _append_tool_consultant_progress(events, feedback_dir / f"{session_tag}_tool_trace.jsonl")
    _append_decision_progress(events, feedback_dir / f"{session_tag}_decision.json")

    research_dir = result_dir / "research_loop"
    scientist_dir = research_dir / "scientist"
    if _recent_tree(scientist_dir, started_at):
        _append_panelist_tool_progress(events, scientist_dir)
        _append_scientist_round_progress(events, scientist_dir)
    if _recent_file(research_dir / "phase0_formulate.json", started_at):
        _append_research_plan_progress(events, research_dir / "phase0_formulate.json")
    if _recent_file(research_dir / "phase1_decision.json", started_at):
        _append_decision_progress(events, research_dir / "phase1_decision.json", title_prefix="Phase 1")
    if _recent_file(research_dir / "phase1_dag_result.json", started_at):
        _append_dag_result_progress(events, research_dir / "phase1_dag_result.json", title_prefix="Phase 1")
    if _recent_file(research_dir / "phase1_analyzer_report.json", started_at):
        _append_analyzer_progress(events, research_dir / "phase1_analyzer_report.json")
    if _recent_file(research_dir / "phase1_update.json", started_at):
        _append_update_progress(events, research_dir / "phase1_update.json")

    _append_dag_directory_progress(events, tool_artifact_dir / "dag", session_tag, started_at=started_at)
    _append_coder_progress(events, tool_artifact_dir / "coder", session_tag, started_at=started_at)

    return _dedupe_events(events)


def _append_tool_consultant_progress(events: list[dict[str, str]], trace_path: Path) -> None:
    for call in _read_jsonl(trace_path):
        tool_name = str(call.get("tool_name") or "").strip()
        if not tool_name:
            continue
        args = call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
        if tool_name.startswith("wiki_") or "wiki" in tool_name:
            query = args.get("query") or args.get("task_id") or args.get("tool_id") or args.get("stage")
            events.append(_event("Tool consultant checked the wiki", f"{tool_name}: {_short(str(query or 'lookup'), 180)}"))
        else:
            events.append(_event("Tool consultant used a planning tool", tool_name))


def _append_panelist_tool_progress(events: list[dict[str, str]], scientist_dir: Path) -> None:
    if not scientist_dir.exists():
        return
    for trace_path in sorted(scientist_dir.glob("*_tool_trace.jsonl")):
        role = _role_label(trace_path.name)
        for call in _read_jsonl(trace_path):
            tool_name = str(call.get("tool_name") or "").strip()
            args = call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
            result = call.get("result")
            if tool_name in {"query_paper_wiki", "search_paper_wiki"}:
                intent = str(args.get("retrieval_intent") or "wiki lookup")
                papers = _extract_tool_papers(result)
                n = len(papers)
                events.append(_event(f"{role} checked paper memory", f"{_short(intent, 180)}\nReturned {n} wiki entries."))
            elif tool_name == "retrieve_literature":
                intent = str(args.get("retrieval_intent") or args.get("base_query") or "fresh retrieval")
                if isinstance(result, dict) and result.get("error"):
                    detail = f"{_short(intent, 180)}\nRetrieval failed: {_short(str(result.get('error')), 260)}"
                    events.append(_event(f"{role} literature retrieval failed", detail))
                    continue
                papers = _extract_tool_papers(result)
                titles = [_short(str(p.get("title") or "Untitled"), 80) for p in papers[:3] if isinstance(p, dict)]
                if papers:
                    detail = f"{_short(intent, 180)}\nRetrieved {len(papers)} judged papers."
                else:
                    detail = f"{_short(intent, 180)}\nNo judged papers passed the relevance filters."
                if isinstance(result, dict) and result.get("persistence_error"):
                    detail += f"\nWiki persistence warning: {_short(str(result.get('persistence_error')), 220)}"
                if titles:
                    detail += "\nTop papers: " + "; ".join(titles)
                events.append(_event(f"{role} retrieved literature", detail))
            elif tool_name == "fetch_paper_section":
                events.append(_event(f"{role} read a paper section", f"{args.get('paper_id', 'paper')} / {args.get('section_type', 'section')}"))
            elif tool_name == "get_related_papers":
                events.append(_event(f"{role} traversed related papers", str(args.get("paper_id") or "paper graph")))


def _extract_tool_papers(result: Any) -> list[Any]:
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        papers = result.get("papers")
        if isinstance(papers, list):
            return papers
        results = result.get("results")
        if isinstance(results, list):
            return results
    return []


def _append_scientist_round_progress(events: list[dict[str, str]], scientist_dir: Path) -> None:
    for name in ("formulate_round1.json", "formulate_brief_round1.json", "update_phase1_round1.json"):
        payload = _read_json(scientist_dir / name)
        if not isinstance(payload, dict):
            continue
        for role in ("biologist", "statistician", "bioinformatician"):
            text = str(payload.get(role) or "")
            parsed = _extract_tag_payload(text, "ROUND1") or _extract_tag_payload(text, "UPDATE")
            if not isinstance(parsed, dict):
                continue
            title = f"{role.capitalize()} panelist summarized reasoning"
            detail = _summarize_panelist_payload(role, parsed)
            if detail:
                events.append(_event(title, detail))


def _append_research_plan_progress(events: list[dict[str, str]], path: Path) -> None:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return
    hypothesis = str(payload.get("consensus_hypothesis") or "").strip()
    plan = payload.get("research_plan") if isinstance(payload.get("research_plan"), dict) else {}
    steps = plan.get("steps") if isinstance(plan, dict) else []
    detail = ""
    if hypothesis:
        detail += f"Hypothesis: {_short(hypothesis, 220)}"
    if isinstance(steps, list) and steps:
        labels = [_step_label(step, idx) for idx, step in enumerate(steps[:4], start=1)]
        detail += ("\n" if detail else "") + f"Plan has {len(steps)} steps: " + "; ".join(labels)
    requirements = payload.get("plan_requirements")
    if isinstance(requirements, dict):
        req = requirements.get("required_statistical_unit") or requirements.get("required_validation") or requirements.get("extension_opportunity")
        if req:
            detail += "\nKey requirement: " + _short(str(req), 180)
    if detail:
        events.append(_event("Research plan generated", detail))


def _append_decision_progress(events: list[dict[str, str]], path: Path, *, title_prefix: str = "") -> None:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return
    prefix = f"{title_prefix} " if title_prefix else ""
    dag_plan = payload.get("dag_plan") if isinstance(payload.get("dag_plan"), dict) else None
    impl_plan = payload.get("implementation_plan") if isinstance(payload.get("implementation_plan"), dict) else None
    if dag_plan:
        layers = dag_plan.get("layers") if isinstance(dag_plan.get("layers"), list) else []
        labels = []
        for layer in layers[:6]:
            if isinstance(layer, dict):
                variants = layer.get("variants") if isinstance(layer.get("variants"), list) else []
                methods = [str(v.get("method")) for v in variants[:3] if isinstance(v, dict) and v.get("method")]
                suffix = f" ({', '.join(methods)})" if methods else ""
                labels.append(f"{layer.get('stage') or layer.get('tool')}{suffix}")
        detail = f"DAG plan with {len(layers)} stages."
        if labels:
            detail += "\n" + " -> ".join(labels)
        events.append(_event(f"{prefix}Tool plan generated", detail))
    elif impl_plan:
        script_name = str(impl_plan.get("script_name") or "custom script")
        objective = str(impl_plan.get("objective") or impl_plan.get("description") or "")
        detail = f"Implementation plan: {script_name}"
        if objective:
            detail += "\n" + _short(objective, 220)
        events.append(_event(f"{prefix}Implementation plan generated", detail))


def _append_dag_directory_progress(events: list[dict[str, str]], dag_root: Path, session_tag: str, *, started_at: float | None) -> None:
    if not dag_root.exists():
        return
    candidates = [dag_root / f"{session_tag}_dag", dag_root / "phase1_dag"]
    candidates.extend(sorted(p for p in dag_root.glob("*_dag") if p.is_dir())[-2:])
    for run_dir in candidates:
        if not run_dir.exists() or not run_dir.is_dir() or not _recent_tree(run_dir, started_at):
            continue
        stage_results = sorted(run_dir.glob("path_*/[0-9][0-9]_*/*result.json"))
        if stage_results:
            latest = stage_results[-6:]
            labels = []
            for result_path in latest:
                stage_name = result_path.parent.name.split("_", 1)[-1]
                result = _read_json(result_path)
                status = str(result.get("status") or "completed") if isinstance(result, dict) else "completed"
                labels.append(f"{stage_name}: {status}")
            events.append(_event("Tool execution progress", "\n".join(labels)))
        result = _read_json(run_dir / "dag_result.json")
        if isinstance(result, dict):
            _append_dag_result_progress(events, run_dir / "dag_result.json")


def _append_dag_result_progress(events: list[dict[str, str]], path: Path, *, title_prefix: str = "") -> None:
    result = _read_json(path)
    if not isinstance(result, dict):
        return
    status = str(result.get("status") or "unknown")
    prefix = f"{title_prefix} " if title_prefix else ""
    if status == "completed":
        best = result.get("best_path") if isinstance(result.get("best_path"), dict) else {}
        metrics = best.get("metrics") if isinstance(best.get("metrics"), dict) else {}
        detail = f"Completed {result.get('paths_completed', 0)} path(s); failed {result.get('paths_failed', 0)}."
        if metrics:
            detail += "\nMetrics: " + _format_metrics(metrics)
        events.append(_event(f"{prefix}Tool execution completed", detail))
    elif status == "failed":
        events.append(_event(f"{prefix}Tool execution failed", _short(str(result.get("error") or "All paths failed."), 240)))


def _append_coder_progress(events: list[dict[str, str]], coder_root: Path, session_tag: str, *, started_at: float | None) -> None:
    if not coder_root.exists():
        return
    candidates = [coder_root / session_tag, coder_root / f"{session_tag}_coder", coder_root / "phase1_coder"]
    candidates.extend(sorted(p for p in coder_root.glob("*") if p.is_dir())[-2:])
    for run_dir in candidates:
        if not run_dir.exists() or not run_dir.is_dir() or not _recent_tree(run_dir, started_at):
            continue
        scripts = sorted(run_dir.glob("*.py"))
        if scripts:
            events.append(_event("Code generated", f"Script: {scripts[-1].name}"))
        report = _read_json(run_dir / "coder_report.json")
        if isinstance(report, dict):
            attempts = report.get("attempt_log") if isinstance(report.get("attempt_log"), list) else []
            detail = f"Coder pipeline {report.get('status', 'unknown')} after {len(attempts)} attempt(s)."
            metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
            if metrics:
                detail += "\nMetrics: " + _format_metrics(metrics)
            if attempts:
                last = attempts[-1]
                if isinstance(last, dict):
                    detail += f"\nLatest step: {last.get('phase', 'attempt')}"
            events.append(_event("Code execution progress", detail))


def _append_analyzer_progress(events: list[dict[str, str]], path: Path) -> None:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return
    summary = payload.get("results_summary") or payload.get("summary") or payload.get("raw")
    if summary:
        events.append(_event("Analyzer interpreted results", _short(str(summary), 260)))


def _append_update_progress(events: list[dict[str, str]], path: Path) -> None:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return
    action = str(payload.get("next_action") or "").strip()
    if action:
        detail = f"Next action: {action}"
        model = payload.get("updated_working_model")
        if isinstance(model, dict) and model.get("current_belief"):
            detail += "\n" + _short(str(model.get("current_belief")), 220)
        events.append(_event("Scientist panel updated the plan", detail))


def _summarize_panelist_payload(role: str, payload: dict[str, Any]) -> str:
    pieces: list[str] = []
    if role == "biologist":
        hypotheses = payload.get("hypotheses") if isinstance(payload.get("hypotheses"), list) else []
        if hypotheses and isinstance(hypotheses[0], dict):
            pieces.append("Hypothesis: " + _short(str(hypotheses[0].get("statement") or ""), 180))
        context = payload.get("biological_context")
        if context:
            pieces.append("Context: " + _short(str(context), 180))
    elif role == "statistician":
        assessment = payload.get("data_assessment") or payload.get("statistical_validity_assessment")
        if assessment:
            pieces.append("Validity: " + _short(str(assessment), 200))
        controls = payload.get("required_controls") or payload.get("next_statistical_requirements")
        if isinstance(controls, list) and controls:
            pieces.append("Key requirement: " + _short(str(controls[0]), 160))
    elif role == "bioinformatician":
        approach = payload.get("recommended_approach") or payload.get("next_computational_approach") or payload.get("approach_assessment")
        if approach:
            pieces.append("Approach: " + _short(str(approach), 200))
    retrieval = payload.get("retrieval_evidence") if isinstance(payload.get("retrieval_evidence"), list) else []
    if retrieval:
        pieces.append(f"Literature intents satisfied: {len(retrieval)}")
    flags = payload.get("cross_role_flags") if isinstance(payload.get("cross_role_flags"), list) else []
    if flags:
        pieces.append(f"Cross-role flags: {len(flags)}")
    return "\n".join(piece for piece in pieces if piece)


def _read_json(path: Path) -> Any:
    if not path.exists() or not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _recent_file(path: Path, started_at: float | None) -> bool:
    if not path.exists():
        return False
    if started_at is None:
        return True
    try:
        return path.stat().st_mtime >= started_at - 2
    except OSError:
        return False


def _recent_tree(path: Path, started_at: float | None) -> bool:
    if not path.exists():
        return False
    if started_at is None:
        return True
    try:
        for item in path.rglob("*"):
            if item.is_file() and item.stat().st_mtime >= started_at - 2:
                return True
    except OSError:
        return False
    return False


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                rows.append(payload)
    except Exception:
        return rows
    return rows


def _extract_tag_payload(text: str, tag: str) -> Any:
    match = re.search(rf"<{tag}>(.*?)</{tag}>", str(text or ""), re.DOTALL)
    if not match:
        return None
    raw = match.group(1).strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    if fence:
        raw = fence.group(1).strip()
    try:
        return json.loads(raw)
    except Exception:
        return None


def _event(title: str, detail: str) -> dict[str, str]:
    return {"title": str(title or "Progress update"), "detail": str(detail or "")}


def _dedupe_events(events: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, str]] = []
    for event in events:
        key = (event.get("title", ""), event.get("detail", ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(event)
    return deduped


def _role_label(filename: str) -> str:
    lower = filename.lower()
    if "biologist" in lower:
        return "Biologist"
    if "statistician" in lower:
        return "Statistician"
    if "bioinformatician" in lower:
        return "Bioinformatician"
    if "adversary" in lower:
        return "Adversary"
    return "Panelist"


def _step_label(step: Any, idx: int) -> str:
    if isinstance(step, dict):
        return _short(str(step.get("step_id") or step.get("biological_goal") or step.get("analysis") or f"step {idx}"), 90)
    return _short(str(step), 90)


def _format_metrics(metrics: dict[str, Any]) -> str:
    parts = []
    for key, value in list(metrics.items())[:5]:
        if isinstance(value, float):
            parts.append(f"{key}={value:.3f}")
        else:
            parts.append(f"{key}={value}")
    return ", ".join(parts)


def _short(text: str, limit: int = 180) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 1)].rstrip() + "…"


def _make_handler(state: _FrontendState):
    class ConsultantFrontendHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            print(f"[frontend] {self.address_string()} - {fmt % args}")

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self) -> None:
            body = HTML_PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _serve_artifact(self) -> None:
            try:
                resolved = _resolve_artifact_request_path(
                    self.path,
                    tool_artifact_dir=state.tool_artifact_dir,
                    result_dir=Path(state.config.result_dir),
                )
            except ValueError:
                self._send_json(400, {"error": "bad path"})
                return
            except PermissionError:
                self._send_json(403, {"error": "forbidden"})
                return
            if not resolved.is_file():
                self._send_json(404, {"error": "not found"})
                return
            mime = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
            body = resolved.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/" or self.path.startswith("/?"):
                self._send_html()
                return
            if self.path == "/status":
                self._send_json(200, state.status())
                return
            if self.path == "/progress":
                self._send_json(200, state.progress())
                return
            if self.path.startswith("/artifacts/"):
                self._serve_artifact()
                return
            self._send_json(404, {"error": "not found"})

        def do_POST(self) -> None:
            if self.path != "/chat":
                self._send_json(404, {"error": "not found"})
                return
            try:
                raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                payload = json.loads(raw.decode("utf-8") or "{}")
                result = state.chat(str(payload.get("message", "")))
                self._send_json(200, result)
            except Exception:
                exc = sys.exc_info()[1]
                self._send_json(500, {"error": html.escape(str(exc))})

    return ConsultantFrontendHandler


def _resolve_repo_path(repo_root: Path, path_value: str | os.PathLike[str]) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else repo_root / path


def _artifact_url_for_path(path: str | os.PathLike[str], *, tool_artifact_dir: Path, result_dir: Path) -> str:
    resolved = Path(path).expanduser().resolve()
    tool_root = tool_artifact_dir.resolve()
    result_root = result_dir.resolve()
    if _is_under(resolved, tool_root):
        relative = resolved.relative_to(tool_root).as_posix()
        return "/artifacts/tool/" + urllib.parse.quote(relative, safe="/")
    if _is_under(resolved, result_root):
        relative = resolved.relative_to(result_root).as_posix()
        return "/artifacts/result/" + urllib.parse.quote(relative, safe="/")
    raise ValueError(f"Artifact path is outside allowed roots: {resolved}")


def _resolve_artifact_request_path(request_path: str, *, tool_artifact_dir: Path, result_dir: Path) -> Path:
    prefix = "/artifacts/"
    if not request_path.startswith(prefix):
        raise ValueError("not an artifact path")
    raw = urllib.parse.unquote(request_path.removeprefix(prefix))
    root_name, sep, relative = raw.partition("/")
    if not sep or not relative:
        raise ValueError("missing artifact root or relative path")
    root_map = {
        "tool": tool_artifact_dir.resolve(),
        "result": result_dir.resolve(),
    }
    root = root_map.get(root_name)
    if root is None:
        raise ValueError("unknown artifact root")
    candidate = (root / relative).resolve()
    if not _is_under(candidate, root):
        raise PermissionError("artifact path escapes allowed root")
    return candidate


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Local web frontend for chatting with the single-cell consultant.")
    parser.add_argument("--input_mod1", required=True, help="Path to the input h5ad file.")
    parser.add_argument("--input_mod2", default=None, help="Optional second modality h5ad file.")
    parser.add_argument("--engine", default="gpt-5")
    parser.add_argument("--fast-engine", default=None, help="Optional faster model for panel retrieval/judging. Defaults to --engine.")
    parser.add_argument("--code-dir", default="saved_code_frontend")
    parser.add_argument("--results-dir", default="results_frontend")
    parser.add_argument("--tool-artifact-dir", default=None, help="Directory for intermediate artifacts produced by tool calls.")
    parser.add_argument("--reticulate-python", default=None, help="Python executable R reticulate should use. Defaults to the Python running this frontend.")
    parser.add_argument("--dataset-dir", default=None)
    parser.add_argument("--rag-root", default="rag_data", help="RAG store root used by the Scientist/Analyzer panels.")
    parser.add_argument("--embedding-backend", choices=["local", "openai"], default="local")
    parser.add_argument("--embedding-model", default=None)
    parser.add_argument("--research-max-phases", type=int, default=5)
    parser.add_argument("--time-budget", type=int, default=3600)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open-browser", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    if not Path(args.input_mod1).exists():
        raise FileNotFoundError(f"input_mod1 not found: {args.input_mod1}")

    state = _FrontendState(args=args)
    server = ThreadingHTTPServer((args.host, args.port), _make_handler(state))
    url = f"http://{args.host}:{args.port}"
    print(f"Consultant frontend running at {url}")
    print(f"Results directory: {state.config.result_dir}")
    print(f"Tool artifact directory: {state.tool_artifact_dir}")
    if args.open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down consultant frontend.")
    finally:
        server.server_close()


if __name__ == "__main__":
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    main()
