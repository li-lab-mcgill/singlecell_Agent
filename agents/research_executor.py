from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, Dict


class SubprocessResearchExecutor:
    """Run the existing research pipeline as a separate subprocess-backed subsystem."""

    def __init__(
        self,
        *,
        repo_root: str | Path,
        engine_name: str,
        input_mod1: str,
        input_mod2: str | None = None,
        dataset_dir: str | None = None,
        time_budget: int = 3600,
        base_artifact_dir: str | Path,
    ):
        self.repo_root = Path(repo_root)
        self.engine_name = engine_name
        self.input_mod1 = str(input_mod1)
        self.input_mod2 = str(input_mod2) if input_mod2 else None
        self.dataset_dir = str(dataset_dir) if dataset_dir else None
        self.time_budget = int(time_budget)
        self.base_artifact_dir = Path(base_artifact_dir)
        self.base_artifact_dir.mkdir(parents=True, exist_ok=True)

    def execute(
        self,
        *,
        user_message: str,
        session_state: Dict[str, Any] | None = None,
        session_tag: str = "research",
    ) -> Dict[str, Any]:
        session_state = dict(session_state or {})
        run_root = self.base_artifact_dir / "research" / session_tag
        code_dir = run_root / "saved_code"
        results_dir = run_root / "results"
        tool_artifact_dir = run_root / "tool_artifacts"
        code_dir.mkdir(parents=True, exist_ok=True)
        results_dir.mkdir(parents=True, exist_ok=True)
        tool_artifact_dir.mkdir(parents=True, exist_ok=True)

        background = _build_research_background(user_message=user_message, session_state=session_state)
        cmd = [
            sys.executable,
            str(self.repo_root / "default.py"),
            "--input_mod1",
            self.input_mod1,
            "--engine",
            self.engine_name,
            "--code-dir",
            str(code_dir),
            "--results-dir",
            str(results_dir),
            "--tool-artifact-dir",
            str(tool_artifact_dir),
            "--time-budget",
            str(self.time_budget),
            "--background",
            background,
        ]
        if self.input_mod2:
            cmd.extend(["--input_mod2", self.input_mod2])
        if self.dataset_dir:
            cmd.extend(["--dataset-dir", self.dataset_dir])

        proc = subprocess.run(
            cmd,
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
        )
        log_path = results_dir / "feedback" / "run_console.log"
        report: Dict[str, Any] = {
            "artifact_dir": str(run_root),
            "results_dir": str(results_dir),
            "stdout": proc.stdout[-8000:],
            "stderr": proc.stderr[-8000:],
        }
        if log_path.exists():
            report["report_path"] = str(log_path)
        if proc.returncode == 0:
            report["status"] = "completed"
            report["message"] = f"Research pipeline completed. Outputs saved in {results_dir}."
        else:
            report["status"] = "failed"
            detail = (proc.stderr or proc.stdout or f"Research pipeline exited with code {proc.returncode}").strip()
            report["error"] = detail[-1200:]
            report["message"] = f"Research pipeline failed. See {results_dir}."
        return report


def _build_research_background(*, user_message: str, session_state: Dict[str, Any]) -> str:
    input_mod1 = str(session_state.get("input_h5ad_path") or "").strip()
    input_mod2 = str(session_state.get("input_mod2_path") or "").strip()
    initial_query = str(session_state.get("initial_query") or "").strip()
    lines = [
        f"Data file: Modality 1: {input_mod1 or 'unknown'}",
        f"Data file: Modality 2: {input_mod2 or 'None'}",
        "DATA: Sparse, high-dimensional single-cell data.",
        "",
        "TASK:",
        str(user_message or "").strip(),
    ]
    if initial_query:
        lines.extend(["", f"INITIAL_SESSION_TASK: {initial_query}"])
    return "\n".join(lines).strip()
