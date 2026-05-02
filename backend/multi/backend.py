from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..refs import ReferenceStore
from ..runners import RunnerSuite

from . import (
    _cross_modality_prediction,
    _foundation_models,
    _grn_inference,
    _joint_differential_expression,
    _joint_rna_velocity,
    _label_transfer,
    _mosaic_integration,
    _paired_integration,
    _unpaired_integration,
)

if TYPE_CHECKING:
    from .. import SingleCellBackend


class MultiBackend:
    """Orchestrator for multimodal (RNA + ATAC) compute methods.

    Holds a back-reference to the top-level SingleCellBackend so methods can
    call into ``backend.rna`` / ``backend.atac`` for modality sub-steps
    (e.g., re-QC the RNA half before paired integration).
    """

    def __init__(self, refs: ReferenceStore, runners: RunnerSuite, parent: "SingleCellBackend"):
        self.refs = refs
        self.runners = runners
        self.parent = parent

    def paired_integrate(self, rna_adata, atac_adata, *, method: str, **kwargs: Any):
        return _paired_integration.dispatch(rna_adata, atac_adata, method=method, refs=self.refs, runners=self.runners, **kwargs)

    def mosaic_integrate(self, adatas, modalities, *, method: str, **kwargs: Any):
        return _mosaic_integration.dispatch(adatas, modalities, method=method, refs=self.refs, runners=self.runners, **kwargs)

    def unpaired_integrate(self, rna_adata, atac_adata, *, method: str, **kwargs: Any):
        return _unpaired_integration.dispatch(rna_adata, atac_adata, method=method, refs=self.refs, runners=self.runners, **kwargs)

    def label_transfer(self, query_adata, *, reference_atlas: str, method: str, modality: str = "rna", **kwargs: Any):
        return _label_transfer.dispatch(query_adata, reference_atlas=reference_atlas, method=method, modality=modality, refs=self.refs, runners=self.runners, **kwargs)

    def cross_modality_predict(self, input_adata, *, source_modality: str, target_modality: str, method: str, **kwargs: Any):
        return _cross_modality_prediction.dispatch(input_adata, source_modality=source_modality, target_modality=target_modality, method=method, refs=self.refs, **kwargs)

    def joint_de(self, rna_adata, atac_adata, *, group_key: str, method: str, **kwargs: Any):
        return _joint_differential_expression.dispatch(rna_adata, atac_adata, group_key=group_key, method=method, runners=self.runners, **kwargs)

    def joint_rna_velocity(self, rna_adata, atac_adata, *, method: str, **kwargs: Any):
        return _joint_rna_velocity.dispatch(rna_adata, atac_adata, method=method, **kwargs)

    def grn_inference(self, rna_adata, atac_adata, *, method: str, gene_annotation: str = "gencode_v44_human", **kwargs: Any):
        return _grn_inference.dispatch(rna_adata, atac_adata, method=method, gene_annotation=gene_annotation, refs=self.refs, runners=self.runners, **kwargs)

    def foundation_model(self, adata, *, model: str, task: str, **kwargs: Any):
        return _foundation_models.dispatch(adata, model=model, task=task, refs=self.refs, **kwargs)
