"""Single-cell analysis backend.

Composition:

    SingleCellBackend
    ├── config     : BackendConfig
    ├── runners    : RunnerSuite                (R + CLI subprocess helpers)
    ├── refs       : ReferenceStore             (static-bulk references, download/cache)
    ├── api        : dict of API clients        (Ensembl, JASPAR, CellxGene, ...)
    ├── rna        : RnaBackend
    ├── atac       : AtacBackend
    ├── multi      : MultiBackend               (back-ref to self for sub-steps)
    ├── eval       : Evaluator                  (silhouette, ARI, NMI, batch_entropy, ...)
    ├── runs       : TrialRegistry              (SQLite-backed leaderboard)
    └── cache      : StepCache                  (hash-keyed step output cache)
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .atac import AtacBackend
from .cache import StepCache
from .config import BackendConfig
from .eval import Evaluator
from .multi import MultiBackend
from .refs import ReferenceStore
from .refs.api_clients import build_default_api_clients
from .rna import RnaBackend
from .runners import RunnerSuite, build_runners
from .runs import TrialRegistry


def context_read_dataset_summary(runtime_context: Any) -> Dict[str, Any]:
    from .context_access import read_dataset_summary

    return read_dataset_summary(runtime_context)


def context_read_label_distribution(runtime_context: Any, label_key: str) -> Dict[str, Any]:
    from .context_access import read_label_distribution

    return read_label_distribution(runtime_context, label_key)


def context_read_prior_resource_summary(runtime_context: Any) -> Dict[str, Any]:
    from .context_access import read_prior_resource_summary

    return read_prior_resource_summary(runtime_context)


def context_check_prior_coverage(runtime_context: Any, resource_name: str) -> Dict[str, Any]:
    from .context_access import check_prior_coverage

    return check_prior_coverage(runtime_context, resource_name)


def context_query_marker_database(runtime_context: Any, tissue: str, species: str) -> Dict[str, Any]:
    from .context_access import query_marker_database

    return query_marker_database(runtime_context, tissue, species)


def context_query_pathway_database(runtime_context: Any, database: str, gene: str) -> Dict[str, Any]:
    from .context_access import query_pathway_database

    return query_pathway_database(runtime_context, database, gene)


class SingleCellBackend:
    config: BackendConfig
    runners: RunnerSuite
    refs: ReferenceStore
    api: Dict[str, Any]
    rna: RnaBackend
    atac: AtacBackend
    multi: MultiBackend
    eval: Evaluator
    runs: TrialRegistry
    cache: StepCache

    def __init__(self, config: Optional[BackendConfig] = None):
        self.config = config or BackendConfig()
        self._runtime_context: Any | None = None
        self.runners = build_runners(
            scratch_dir=self.config.scratch_dir,
            r_executable=self.config.r_executable,
            r_scripts_dir=self.config.r_scripts_dir,
            reticulate_python=self.config.reticulate_python,
        )
        self.refs = ReferenceStore(self.config)
        self.api = build_default_api_clients()
        self.rna = RnaBackend(refs=self.refs, runners=self.runners)
        self.atac = AtacBackend(refs=self.refs, runners=self.runners)
        self.multi = MultiBackend(refs=self.refs, runners=self.runners, parent=self)

        runs_db = self.config.cache_dir / "runs.db"
        self.eval = Evaluator()
        self.runs = TrialRegistry(db_path=runs_db)
        self.cache = StepCache(
            self.config.cache_dir,
            max_gb=self.config.cache_max_gb,
            use_hardlinks=self.config.use_hardlinks,
        )

    def bind_runtime_context(self, context: Any) -> None:
        self._runtime_context = context

    def _require_runtime_context(self) -> Any:
        if self._runtime_context is None:
            raise RuntimeError("Backend runtime context is not bound.")
        return self._runtime_context

    def read_dataset_summary(self) -> Dict[str, Any]:
        return context_read_dataset_summary(self._require_runtime_context())

    def read_label_distribution(self, label_key: str) -> Dict[str, Any]:
        return context_read_label_distribution(self._require_runtime_context(), label_key)

    def read_prior_resource_summary(self) -> Dict[str, Any]:
        return context_read_prior_resource_summary(self._require_runtime_context())

    def check_prior_coverage(self, resource_name: str) -> Dict[str, Any]:
        return context_check_prior_coverage(self._require_runtime_context(), resource_name)

    def query_marker_database(self, tissue: str, species: str) -> Dict[str, Any]:
        return context_query_marker_database(self._require_runtime_context(), tissue, species)

    def query_pathway_database(self, database: str, gene: str) -> Dict[str, Any]:
        return context_query_pathway_database(self._require_runtime_context(), database, gene)

    def supported_capabilities(self) -> Dict[str, Any]:
        """Return implemented method choices used by planning compatibility tests."""
        return {
            "rna": {
                "qc": {"supported_methods": ["basic", "scrublet"]},
                "normalize": {"supported_methods": ["log1p"]},
                "features": {"supported_methods": ["seurat_v3", "cellranger", "scanpy_hvg"]},
                "embed": {"supported_methods": ["pca", "scvi", "seurat_pca", "scanvi"]},
                "cluster": {"supported_methods": ["leiden", "louvain"]},
                "annotate": {"supported_methods": ["gpt4", "cellmarker", "celltypist"]},
            }
        }

    def health_check(self) -> Dict[str, Any]:
        return {
            "r_available": self.runners.r.is_available(),
            "reticulate_python": str(self.config.reticulate_python) if self.config.reticulate_python else None,
            "r_script_dir": str(self.config.r_scripts_dir),
            "cache_dir": str(self.config.cache_dir),
            "scratch_dir": str(self.config.scratch_dir),
            "n_references_cached_on_disk": sum(1 for m in self.refs.list_available() if m.on_disk),
            "n_references_in_memory": sum(1 for m in self.refs.list_available() if m.loaded_in_memory),
            "api_clients": sorted(self.api.keys()),
        }


__all__ = [
    "SingleCellBackend",
    "BackendConfig",
    "ReferenceStore",
    "RunnerSuite",
    "RnaBackend",
    "AtacBackend",
    "MultiBackend",
    "Evaluator",
    "TrialRegistry",
    "StepCache",
]
