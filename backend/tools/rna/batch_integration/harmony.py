"""Harmony batch correction on a precomputed embedding."""

from __future__ import annotations


def run(
    adata,
    *,
    batch_key: str,
    embedding_key: str = "X_pca",
    n_pcs: int = 50,
    theta: float = 2.0,
):
    import scanpy as sc
    from harmonypy import run_harmony

    if batch_key not in adata.obs:
        raise ValueError(f"batch_key '{batch_key}' not found in adata.obs.")
    if embedding_key not in adata.obsm:
        if embedding_key == "X_pca":
            sc.pp.pca(adata, n_comps=n_pcs)
        else:
            raise ValueError(f"embedding_key '{embedding_key}' not found in adata.obsm.")

    output_key = "X_harmony" if embedding_key == "X_pca" else f"{embedding_key}_harmony"
    ho = run_harmony(adata.obsm[embedding_key], adata.obs, batch_key, theta=theta)
    adata.obsm[output_key] = ho.Z_corr.T
    adata.uns["batch_integration"] = {
        "method": "harmony",
        "batch_key": batch_key,
        "input_embedding_key": embedding_key,
        "obsm_key": output_key,
    }
    return adata
