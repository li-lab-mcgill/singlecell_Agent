from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Literal, Optional


class RRunner:
    """Wraps subprocess calls to Rscript.

    Every R script is expected to accept `--args-json <path>` where the file
    holds a JSON dict of parameters. The script writes its result as JSON to
    stdout (if returns="json") or to a path named in `output_path` inside the
    args dict.
    """

    def __init__(
        self,
        r_executable: Optional[Path] = None,
        scratch_dir: Optional[Path] = None,
        script_dir: Optional[Path] = None,
        reticulate_python: Optional[Path] = None,
    ):
        self.r_executable = str(r_executable) if r_executable else (shutil.which("Rscript") or "Rscript")
        self.scratch_dir = Path(scratch_dir) if scratch_dir else Path(tempfile.gettempdir())
        self.script_dir = Path(script_dir) if script_dir else None
        self.reticulate_python = Path(reticulate_python) if reticulate_python else None

    def is_available(self) -> bool:
        return shutil.which(self.r_executable) is not None

    def installed_packages(self) -> list[str]:
        if not self.is_available():
            return []
        try:
            result = subprocess.run(
                [self.r_executable, "-e", 'cat(paste(rownames(installed.packages()), collapse=","))'],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return []
            return [p.strip() for p in result.stdout.strip().split(",") if p.strip()]
        except Exception:
            return []

    def run_script(
        self,
        script_name: str,
        args: Dict[str, Any],
        returns: Literal["json", "stdout", "none"] = "json",
        timeout: Optional[int] = 3600,
    ) -> Any:
        if not self.is_available():
            raise RuntimeError(f"Rscript not found at {self.r_executable}")

        if self.script_dir and not Path(script_name).is_absolute():
            script_path = self.script_dir / script_name
        else:
            script_path = Path(script_name)

        if not script_path.exists():
            raise FileNotFoundError(f"R script not found: {script_path}")

        self.scratch_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, dir=str(self.scratch_dir)
        ) as f:
            json.dump(args, f, default=str)
            args_path = f.name

        try:
            env = os.environ.copy()
            if self.reticulate_python:
                env["RETICULATE_PYTHON"] = str(self.reticulate_python)
            proc = subprocess.run(
                [self.r_executable, "--vanilla", str(script_path), "--args-json", args_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"R script {script_path.name} failed (exit {proc.returncode}):\n"
                    f"STDERR:\n{proc.stderr}\nSTDOUT:\n{proc.stdout}"
                )
            if returns == "json":
                stdout = proc.stdout.strip()
                if not stdout:
                    return {}
                # Some R packages print to stdout; take the last valid JSON line.
                for line in reversed(stdout.splitlines()):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        return json.loads(line)
                    except json.JSONDecodeError:
                        continue
                raise RuntimeError(f"R script {script_path.name} did not emit JSON. STDOUT:\n{stdout}")
            if returns == "stdout":
                return proc.stdout
            return None
        finally:
            Path(args_path).unlink(missing_ok=True)
