from __future__ import annotations

import argparse
import html
import json
import mimetypes
import os
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
      width: min(1180px, calc(100vw - 28px));
      margin: 0 auto;
      padding: 28px 0;
      display: grid;
      grid-template-columns: 330px minmax(0, 1fr);
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
    @media (max-width: 860px) {
      .shell { grid-template-columns: 1fr; }
      aside { position: static; height: auto; }
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
  </div>
  <script>
    const messages = document.getElementById("messages");
    const form = document.getElementById("chatForm");
    const input = document.getElementById("messageInput");
    const button = document.getElementById("sendButton");

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
        const extra = `route: <code>${route.route || "unknown"}</code><br>decision: <code>${decision.decision || "none"}</code><br>status: <code>${result.status || "unknown"}</code><br>tools: ${tools || "<code>none</code>"}<br>session: <code>${data.session_tag}</code>`;
        addMessage("assistant", result.search_summary || result.recommendation || result.message || JSON.stringify(data, null, 2), extra, false, result.images || []);
      } catch (err) {
        addMessage("assistant", String(err.message || err), null, true);
      } finally {
        button.disabled = false;
        button.textContent = "Send";
        input.focus();
      }
    });

    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
        form.requestSubmit();
      }
    });

    loadStatus();
  </script>
</body>
</html>
"""


class _FrontendState:
    def __init__(self, *, args: argparse.Namespace):
        import textgrad as tg

        from agents.coder import CoderAgent
        from agents.dag_executor import DagExecutor
        from agents.research_executor import SubprocessResearchExecutor
        from agents.result_summarizer import ResultSummarizer
        from agents.session_dispatcher import SessionDispatcher
        from agents.session_router import SessionRouter
        from agents.session_state import SessionStateStore
        from agents.tool_consultant import ToolConsultantAgent
        from backend import BackendConfig, SingleCellBackend
        from pipelines.config import Config

        self.args = args
        self.repo_root = Path(__file__).resolve().parents[1]
        self.turn = 0
        self.lock = threading.Lock()

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
        )

    def status(self) -> dict[str, Any]:
        return {
            "engine": self.args.engine,
            "input_h5ad_path": self.args.input_mod1,
            "result_dir": self.config.result_dir,
            "tool_artifact_dir": str(self.tool_artifact_dir),
            "initial_query": self.session_store.snapshot().get("initial_query"),
        }

    def chat(self, message: str) -> dict[str, Any]:
        clean_message = str(message or "").strip()
        if not clean_message:
            raise ValueError("message must be non-empty")
        with self.lock:
            self.turn += 1
            session_tag = f"frontend_consultant_{self.turn:03d}"
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
            return result


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
    parser.add_argument("--code-dir", default="saved_code_frontend")
    parser.add_argument("--results-dir", default="results_frontend")
    parser.add_argument("--tool-artifact-dir", default=None, help="Directory for intermediate artifacts produced by tool calls.")
    parser.add_argument("--reticulate-python", default=None, help="Python executable R reticulate should use. Defaults to the Python running this frontend.")
    parser.add_argument("--dataset-dir", default=None)
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
