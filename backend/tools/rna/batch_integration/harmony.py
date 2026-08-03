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
    import subprocess, sys
    try:
        from harmonypy import run_harmony
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "harmonypy"], check=True)
        from harmonypy import run_harmony
    import scanpy as sc

    if batch_key not in adata.obs:
        raise ValueError(f"batch_key '{batch_key}' not found in adata.obs.")
    if embedding_key not in adata.obsm:
        if embedding_key == "X_pca":
            sc.pp.pca(adata, n_comps=n_pcs)
        else:
            raise ValueError(f"embedding_key '{embedding_key}' not found in adata.obsm.")

    output_key = "X_harmony" if embedding_key == "X_pca" else f"{embedding_key}_harmony"
    ho = run_harmony(adata.obsm[embedding_key], adata.obs, batch_key, theta=theta)
    # harmonypy ≥2.0 returns Z_corr as (cells × PCs); older versions returned (PCs × cells)
    corrected = ho.Z_corr
    if corrected.shape[0] != adata.n_obs:
        corrected = corrected.T
    if corrected.shape[0] != adata.n_obs:
        raise RuntimeError(
            f"Harmony output has shape {corrected.shape}, expected first dimension n_obs={adata.n_obs}."
        )
    adata.obsm[output_key] = corrected
    adata.uns["batch_integration"] = {
        "method": "harmony",
        "batch_key": batch_key,
        "input_embedding_key": embedding_key,
        "obsm_key": output_key,
    }
    return adata
