"""Highly variable gene selection using Seurat v3 method (variance-stabilized dispersion)."""

from __future__ import annotations


def run(
    adata,
    *,
    n_top: int = 2000,
    batch_key: str | None = None,
):
    import scanpy as sc

    kwargs = {"flavor": "seurat_v3", "n_top_genes": n_top, "batch_key": batch_key}
    if "counts" in getattr(adata, "layers", {}):
        kwargs["layer"] = "counts"
    sc.pp.highly_variable_genes(adata, **kwargs)
    adata.uns["feature_selection"] = {"method": "seurat_v3", "n_top": n_top, "batch_key": batch_key}
    return adata
