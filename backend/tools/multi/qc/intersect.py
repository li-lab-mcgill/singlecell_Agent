"""Multi-omic QC: intersect cells present in both RNA and ATAC modalities.

Must be run before any joint embedding. Ensures both AnnData objects contain
exactly the same cells in the same order.
"""

from __future__ import annotations

from pathlib import Path


def run(
    adata,
    *,
    atac_h5ad_path: str | Path,
    output_atac_h5ad_path: str | Path | None = None,
) -> object:
    """Intersect cells between RNA and ATAC modalities.

    Keeps only barcodes present in both adata (RNA) and the ATAC AnnData.
    Reorders both to the same cell order. The filtered ATAC AnnData is
    written to output_atac_h5ad_path (or overwrites atac_h5ad_path if not given).

    Args:
        adata: RNA AnnData.
        atac_h5ad_path: Path to ATAC AnnData h5ad file.
        output_atac_h5ad_path: Where to write the filtered ATAC AnnData.
                                If None, overwrites atac_h5ad_path.

    Returns:
        RNA adata subsetted to shared cells, with adata.uns["atac_h5ad_path"]
        pointing to the filtered ATAC h5ad.
    """
    import anndata as ad

    atac_path = Path(atac_h5ad_path)
    if not atac_path.exists():
        raise FileNotFoundError(f"ATAC AnnData not found: {atac_path}")

    atac = ad.read_h5ad(atac_path)

    shared = list(set(adata.obs_names) & set(atac.obs_names))
    if not shared:
        raise ValueError(
            f"No shared barcodes between RNA ({adata.n_obs} cells) and "
            f"ATAC ({atac.n_obs} cells). Check that barcodes match."
        )

    n_rna_before, n_atac_before = adata.n_obs, atac.n_obs
    shared_sorted = sorted(shared)

    adata = adata[shared_sorted].copy()
    atac = atac[shared_sorted].copy()

    out_atac_path = Path(output_atac_h5ad_path) if output_atac_h5ad_path else atac_path
    atac.write_h5ad(out_atac_path)

    adata.uns["atac_h5ad_path"] = str(out_atac_path)
    adata.uns["multi_qc"] = {
        "n_rna_before": n_rna_before,
        "n_atac_before": n_atac_before,
        "n_shared": len(shared_sorted),
        "n_dropped_rna": n_rna_before - len(shared_sorted),
        "n_dropped_atac": n_atac_before - len(shared_sorted),
    }

    return adata
