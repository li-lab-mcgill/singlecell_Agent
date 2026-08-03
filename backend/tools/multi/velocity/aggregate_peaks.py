"""ATAC peak → gene aggregation and TF-IDF normalization for MultiVelo.

Converts the ATAC AnnData from peak space to gene space using Cell Ranger ARC
output files (atac_peak_annotation.tsv and feature_linkage.bedpe), then applies
TF-IDF normalization. Must run before multi_velocity_knn_smooth.

After this tool, adata_atac.layers["Mc"] contains TF-IDF normalized gene-level
chromatin accessibility (shared var_names with RNA adata).
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def run(
    adata,
    *,
    atac_h5ad_path: str | Path | None = None,
    peaks_annot_path: str | Path,
    linkage_path: str | Path,
    use_gene_id: bool = False,
    tfidf_scale_factor: float = 1e4,
    output_dir: Path | None = None,
) -> object:
    """Aggregate 10X ATAC peaks to gene-level and apply TF-IDF normalization.

    Args:
        adata: RNA AnnData. Used to determine shared gene list and to read
               adata.uns["atac_h5ad_path"] if atac_h5ad_path is not provided.
        atac_h5ad_path: Path to ATAC AnnData with peak-level var_names
                        (chr:start-end format). Falls back to
                        adata.uns["atac_h5ad_path"] if not provided.
        peaks_annot_path: Path to atac_peak_annotation.tsv from Cell Ranger ARC.
                          Required by mv.aggregate_peaks_10x.
        linkage_path: Path to feature_linkage.bedpe from Cell Ranger ARC.
                      Required by mv.aggregate_peaks_10x.
        use_gene_id: If True, var_names are Ensembl IDs; if False (default),
                     var_names are gene symbols. Must match RNA adata.
        tfidf_scale_factor: Scale factor for TF-IDF normalization (default 1e4).
        output_dir: Unused (reserved for future outputs). Saved ATAC adata is
                    always written back to its original path.

    Returns:
        adata (RNA) with adata.uns["velocity_aggregate_peaks"] metadata written.
        ATAC adata is updated in-place and saved back to atac_h5ad_path.
    """
    atac_path = _resolve_atac_path(adata, atac_h5ad_path)
    return _run_aggregate_peaks(
        adata,
        atac_path=atac_path,
        peaks_annot_path=Path(peaks_annot_path),
        linkage_path=Path(linkage_path),
        use_gene_id=use_gene_id,
        tfidf_scale_factor=tfidf_scale_factor,
    )


from backend.tools.multi.velocity._utils import resolve_atac_path as _resolve_atac_path


def _run_aggregate_peaks(
    adata,
    *,
    atac_path,
    peaks_annot_path,
    linkage_path,
    use_gene_id,
    tfidf_scale_factor,
):
    import anndata as ad
    import multivelo as mv

    for p in (peaks_annot_path, linkage_path):
        if not p.exists():
            raise FileNotFoundError(
                f"Required Cell Ranger ARC file not found: {p}\n"
                "These files are produced by cellranger-arc count:\n"
                "  - atac_peak_annotation.tsv\n"
                "  - feature_linkage.bedpe"
            )

    adata_atac = ad.read_h5ad(atac_path)
    logger.info(
        "ATAC adata loaded: %d cells × %d peaks", adata_atac.n_obs, adata_atac.n_vars
    )
    n_atac_peaks_before = adata_atac.n_vars

    # Aggregate peaks → gene-level accessibility
    mv.aggregate_peaks_10x(
        adata_atac,
        peaks_annot_path=str(peaks_annot_path),
        linkage_path=str(linkage_path),
        use_gene_id=use_gene_id,
        verbose=False,
    )
    logger.info(
        "After aggregation: %d cells × %d genes", adata_atac.n_obs, adata_atac.n_vars
    )

    # Validate gene overlap with RNA adata
    shared_genes = list(set(adata.var_names) & set(adata_atac.var_names))
    if not shared_genes:
        raise ValueError(
            f"No shared genes between RNA ({adata.n_vars} genes) and "
            f"gene-level ATAC ({adata_atac.n_vars} genes). "
            "Check that use_gene_id matches the var_name convention in both AnnDatas."
        )
    n_shared = len(shared_genes)
    logger.info("Shared genes between RNA and ATAC: %d", n_shared)

    # TF-IDF normalization → writes adata_atac.layers["Mc"]
    mv.tfidf_norm(adata_atac, scale_factor=tfidf_scale_factor)
    logger.info("TF-IDF normalization complete → adata_atac.layers['Mc']")

    # Save updated ATAC adata back to disk
    adata_atac.write_h5ad(atac_path)
    logger.info("ATAC adata saved back to %s", atac_path)

    adata.uns["velocity_aggregate_peaks"] = {
        "n_atac_peaks_before": n_atac_peaks_before,
        "n_atac_genes_after": adata_atac.n_vars,
        "n_shared_genes": n_shared,
        "tfidf_applied": True,
        "tfidf_scale_factor": tfidf_scale_factor,
        "use_gene_id": use_gene_id,
    }

    return adata
