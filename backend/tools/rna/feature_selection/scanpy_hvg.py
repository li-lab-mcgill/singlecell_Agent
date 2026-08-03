"""Highly variable gene selection using Scanpy default (Seurat dispersion) method."""

from __future__ import annotations


def run(
    adata,
    *,
    n_top: int = 2000,
    batch_key: str | None = None,
):
    import scanpy as sc

    if batch_key and batch_key not in adata.obs:
        raise ValueError(f"batch_key '{batch_key}' not found in adata.obs.")
    sc.pp.highly_variable_genes(adata, flavor="seurat", n_top_genes=n_top, batch_key=batch_key)
    adata.uns["feature_selection"] = {"method": "scanpy_hvg", "n_top": n_top, "batch_key": batch_key}
    return adata
