"""ATAC batch integration: Harmony, scVI-ATAC, LIGER-ATAC."""

from __future__ import annotations

from typing import Any

KNOWN_METHODS = ("harmony", "scvi_atac", "liger_atac")


def dispatch(
    adata,
    *,
    method: str,
    batch_key: str,
    embedding_key: str = "X_lsi",
    refs=None,
    runners=None,
    **kwargs: Any,
):
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown atac.integrate method: {method}. Choose from {KNOWN_METHODS}.")
    if not batch_key:
        raise ValueError("batch_key is required for ATAC batch integration.")
    if batch_key not in adata.obs:
        raise ValueError(f"batch_key '{batch_key}' not found in adata.obs.")
    if method == "harmony":
        return _run_harmony(adata, batch_key=batch_key, embedding_key=embedding_key, **kwargs)
    raise NotImplementedError(
        f"atac.integrate(method='{method}') is not implemented yet. "
        "scVI-ATAC requires scvi-tools peak setup; LIGER-ATAC requires an R runner."
    )


def _run_harmony(
    adata,
    *,
    batch_key: str,
    embedding_key: str = "X_lsi",
    theta: float = 2.0,
    **_: Any,
):
    from harmonypy import run_harmony

    if embedding_key not in adata.obsm:
        raise ValueError(f"embedding_key '{embedding_key}' not in adata.obsm. Run atac_tfidf_lsi first.")
    output_key = "X_harmony_lsi" if embedding_key == "X_lsi" else f"{embedding_key}_harmony"
    ho = run_harmony(adata.obsm[embedding_key], adata.obs, batch_key, theta=theta)
    adata.obsm[output_key] = ho.Z_corr.T
    adata.uns["batch_integration"] = {
        "method": "harmony",
        "batch_key": batch_key,
        "input_embedding_key": embedding_key,
        "obsm_key": output_key,
        "theta": theta,
    }
    return adata
