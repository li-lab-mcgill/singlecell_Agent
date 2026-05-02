from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .cli_runner import CliRunner
from .r_runner import RRunner


@dataclass
class RunnerSuite:
    r: RRunner
    cli: CliRunner
    scratch_dir: Path


def build_runners(
    scratch_dir: Path,
    r_executable: Optional[Path] = None,
    r_scripts_dir: Optional[Path] = None,
    reticulate_python: Optional[Path] = None,
) -> RunnerSuite:
    return RunnerSuite(
        r=RRunner(
            r_executable=r_executable,
            scratch_dir=scratch_dir,
            script_dir=r_scripts_dir,
            reticulate_python=reticulate_python,
        ),
        cli=CliRunner(scratch_dir=scratch_dir),
        scratch_dir=scratch_dir,
    )


__all__ = ["RRunner", "CliRunner", "RunnerSuite", "build_runners"]
