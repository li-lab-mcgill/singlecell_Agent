from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional


class CliRunner:
    """Wraps subprocess calls to command-line tools (MACS3, samtools, bedtools, ...)."""

    def __init__(self, scratch_dir: Optional[Path] = None):
        self.scratch_dir = Path(scratch_dir) if scratch_dir else None

    def which(self, binary: str) -> Optional[str]:
        return shutil.which(binary)

    def run(
        self,
        cmd: List[str],
        *,
        cwd: Optional[Path] = None,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None,
        check: bool = True,
        capture_output: bool = True,
    ) -> subprocess.CompletedProcess:
        binary = cmd[0]
        if not Path(binary).exists() and self.which(binary) is None:
            raise FileNotFoundError(f"CLI binary not found on PATH: {binary}")

        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            cwd=str(cwd) if cwd else None,
            timeout=timeout,
            env=env,
        )
        if check and result.returncode != 0:
            preview = " ".join(cmd[:4])
            raise RuntimeError(
                f"CLI command `{preview}...` failed (exit {result.returncode}):\n"
                f"STDERR:\n{result.stderr}"
            )
        return result
