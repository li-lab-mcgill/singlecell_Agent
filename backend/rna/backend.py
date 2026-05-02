from __future__ import annotations

from typing import Any, Optional

from ..refs import ReferenceStore
from ..runners import RunnerSuite
from ..types import CCCResult, DEResult

from . import (
    _2d_projection,
    _batch_integration,
    _cell_cell_communication,
    _celltype_annotation,
    _clustering,
    _differential_expression,
    _dimensionality_reduction,
    _feature_selection,
    _gene_program_inference,
    _imputation,
    _normalization,
    _perturbation_analysis,
    _quality_control,
    _rna_velocity,
    _trajectory_inference,
)


class RnaBackend:
    """Orchestrator for RNA compute methods.

    Each public method is a thin adapter that validates inputs and delegates
    to a per-task module's dispatcher. Method modules never reach back here.
    """

    def __init__(self, refs: ReferenceStore, runners: RunnerSuite):
        self.refs = refs
        self.runners = runners

    # ---------------- Phase A: implemented ----------------

    def qc(self, adata, *, method: str = "basic", **kwargs: Any):
        return _quality_control.dispatch(adata, method=method, runners=self.runners, **kwargs)

    def normalize(self, adata, *, method: str = "log1p", **kwargs: Any):
        return _normalization.dispatch(adata, method=method, runners=self.runners, **kwargs)

    def select_features(self, adata, *, method: str = "seurat_v3", **kwargs: Any):
        return _feature_selection.dispatch(adata, method=method, **kwargs)

    def embed(self, adata, *, method: str, **kwargs: Any):
        return _dimensionality_reduction.dispatch(
            adata, method=method, refs=self.refs, runners=self.runners, **kwargs
        )

    def integrate(self, adata, *, method: str, batch_key: str, **kwargs: Any):
        return _batch_integration.dispatch(
            adata, method=method, batch_key=batch_key, refs=self.refs, runners=self.runners, **kwargs
        )

    def cluster(self, adata, *, embedding_key: str, method: str = "leiden", **kwargs: Any):
        return _clustering.dispatch(adata, embedding_key=embedding_key, method=method, **kwargs)

    def annotate(self, adata, *, method: str, **kwargs: Any):
        return _celltype_annotation.dispatch(adata, method=method, refs=self.refs, runners=self.runners, **kwargs)

    def differential_expression(self, adata, *, group_key: str, method: str = "wilcoxon", **kwargs: Any) -> DEResult:
        return _differential_expression.dispatch(adata, group_key=group_key, method=method, runners=self.runners, **kwargs)

    def visualize(self, adata, *, method: str, embedding_key: str, **kwargs: Any):
        return _2d_projection.dispatch(adata, method=method, embedding_key=embedding_key, **kwargs)

    # ---------------- Phases B+: scaffolded stubs ----------------

    def gene_programs(self, adata, *, method: str, **kwargs: Any):
        return _gene_program_inference.dispatch(adata, method=method, refs=self.refs, runners=self.runners, **kwargs)

    def trajectory(self, adata, *, method: str, **kwargs: Any):
        return _trajectory_inference.dispatch(adata, method=method, **kwargs)

    def rna_velocity(self, adata, *, method: str, **kwargs: Any):
        return _rna_velocity.dispatch(adata, method=method, **kwargs)

    def perturbation(self, adata, *, method: str, **kwargs: Any):
        return _perturbation_analysis.dispatch(adata, method=method, **kwargs)

    def impute(self, adata, *, method: str, **kwargs: Any):
        return _imputation.dispatch(adata, method=method, **kwargs)

    def cell_cell_comm(self, adata, *, method: str, **kwargs: Any) -> CCCResult:
        return _cell_cell_communication.dispatch(adata, method=method, refs=self.refs, **kwargs)
