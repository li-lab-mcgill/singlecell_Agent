from __future__ import annotations

from typing import Any, Optional

from ..refs import ReferenceStore
from ..runners import RunnerSuite

from . import (
    _batch_integration,
    _celltype_annotation,
    _clustering,
    _differential_accessibility,
    _feature_matrix_construction,
    _gene_activity_score,
    _motif_enrichment,
    _peak_calling,
    _peak_to_gene_linking,
    _quality_control,
    _tfidf_lsi,
    _trajectory_inference,
)


class AtacBackend:
    """Orchestrator for scATAC-seq compute methods.

    Implemented modules perform their own input-contract validation and write
    standardized outputs such as X_lsi, lsi_clusters, and typed result objects.
    Remaining R-heavy methods fail explicitly in their module dispatchers.
    """

    def __init__(self, refs: ReferenceStore, runners: RunnerSuite):
        self.refs = refs
        self.runners = runners

    def qc(self, adata, *, method: str = "basic", **kwargs: Any):
        return _quality_control.dispatch(adata, method=method, refs=self.refs, **kwargs)

    def peak_calling(self, *, fragments_path, output_peaks_path, method: str = "macs3", **kwargs: Any):
        return _peak_calling.dispatch(
            fragments_path=fragments_path,
            output_peaks_path=output_peaks_path,
            method=method,
            refs=self.refs,
            runners=self.runners,
            **kwargs,
        )

    def feature_matrix(self, adata, *, method: str = "peaks", **kwargs: Any):
        return _feature_matrix_construction.dispatch(adata, method=method, refs=self.refs, **kwargs)

    def tfidf_lsi(self, adata, *, n_components: int = 50, **kwargs: Any):
        return _tfidf_lsi.dispatch(adata, n_components=n_components, **kwargs)

    def integrate(self, adata, *, method: str, batch_key: str, **kwargs: Any):
        return _batch_integration.dispatch(adata, method=method, batch_key=batch_key, refs=self.refs, runners=self.runners, **kwargs)

    def cluster(self, adata, *, embedding_key: str = "X_lsi", **kwargs: Any):
        return _clustering.dispatch(adata, embedding_key=embedding_key, **kwargs)

    def gene_activity(self, adata, *, method: str = "archr", gene_annotation: str = "gencode_v44_human", **kwargs: Any):
        return _gene_activity_score.dispatch(adata, method=method, gene_annotation=gene_annotation, refs=self.refs, runners=self.runners, **kwargs)

    def motif_enrichment(self, adata, *, motif_db: str, method: str = "chromvar", **kwargs: Any):
        return _motif_enrichment.dispatch(adata, motif_db=motif_db, method=method, refs=self.refs, runners=self.runners, **kwargs)

    def differential_accessibility(self, adata, *, group_key: str, method: str = "wilcoxon", **kwargs: Any):
        return _differential_accessibility.dispatch(adata, group_key=group_key, method=method, runners=self.runners, **kwargs)

    def peak_to_gene_linking(self, adata, *, method: str = "cicero", gene_annotation: str = "gencode_v44_human", **kwargs: Any):
        return _peak_to_gene_linking.dispatch(adata, method=method, gene_annotation=gene_annotation, refs=self.refs, runners=self.runners, **kwargs)

    def trajectory(self, adata, *, embedding_key: str = "X_lsi", method: str = "paga", **kwargs: Any):
        return _trajectory_inference.dispatch(adata, embedding_key=embedding_key, method=method, **kwargs)

    def annotate(self, adata, *, method: str = "rna_label_transfer", **kwargs: Any):
        return _celltype_annotation.dispatch(adata, method=method, refs=self.refs, runners=self.runners, **kwargs)
