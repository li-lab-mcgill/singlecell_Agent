from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class BackendConfig:
    """Runtime configuration for the single-cell backend.

    Passed once at backend construction time; held by RunnerSuite and
    ReferenceStore. Sub-backends borrow references to those.
    """

    cache_dir: Path = field(default_factory=lambda: Path.home() / ".sc_agent_cache")
    scratch_dir: Path = field(default_factory=lambda: Path("/tmp/sc_agent_scratch"))
    n_threads: int = 4
    memory_budget_gb: float = 16.0
    r_executable: Optional[Path] = None
    reticulate_python: Optional[Path] = None
    log_dir: Optional[Path] = None
    r_scripts_dir: Optional[Path] = None
    compress_h5ad: bool = True
    keep_intermediates: bool = False
    keep_top_k_paths: int = 3
    cache_max_gb: float = 20.0
    use_hardlinks: bool = True
    cleanup_existing_artifacts: bool = False

    def __post_init__(self) -> None:
        self.cache_dir = Path(self.cache_dir)
        self.scratch_dir = Path(self.scratch_dir)
        if self.r_executable is not None:
            self.r_executable = Path(self.r_executable)
        if self.reticulate_python is not None:
            self.reticulate_python = Path(self.reticulate_python)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.scratch_dir.mkdir(parents=True, exist_ok=True)
        if self.log_dir is not None:
            self.log_dir = Path(self.log_dir)
            self.log_dir.mkdir(parents=True, exist_ok=True)
        if self.r_scripts_dir is None:
            self.r_scripts_dir = Path(__file__).parent / "r_scripts"
        else:
            self.r_scripts_dir = Path(self.r_scripts_dir)
