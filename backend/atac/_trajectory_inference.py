"""ATAC trajectory inference: PAGA, Slingshot (run on LSI embedding)."""

from __future__ import annotations

from typing import Any, Optional

KNOWN_METHODS = ("paga", "slingshot")


def dispatch(
    adata,
    *,
    embedding_key: str = "X_lsi",
    method: str = "paga",
    group_key: Optional[str] = None,
    root_cells=None,
    n_neighbors: int = 15,
    **kwargs: Any,
):
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown atac.trajectory method: {method}. Choose from {KNOWN_METHODS}.")
    if method == "paga":
        return _run_paga(
            adata,
            embedding_key=embedding_key,
            group_key=group_key,
            root_cells=root_cells,
            n_neighbors=n_neighbors,
        )
    raise NotImplementedError(
        "atac.trajectory(method='slingshot') requires an R slingshot runner and is not implemented yet."
    )


def _run_paga(
    adata,
    *,
    embedding_key: str,
    group_key: Optional[str],
    root_cells: Any,
    n_neighbors: int,
):
    import scanpy as sc

    if embedding_key not in adata.obsm:
        raise ValueError(f"embedding_key '{embedding_key}' not in adata.obsm. Run atac_tfidf_lsi first.")
    group_key = group_key or getattr(adata, "uns", {}).get("clustering", {}).get("cluster_key")
    if not group_key:
        raise ValueError("PAGA trajectory requires group_key or adata.uns['clustering']['cluster_key'].")
    if group_key not in adata.obs:
        raise ValueError(f"group_key '{group_key}' not found in adata.obs.")

    sc.pp.neighbors(adata, n_neighbors=n_neighbors, use_rep=embedding_key)
    sc.tl.paga(adata, groups=group_key)
    adata.uns["trajectory"] = {
        "method": "paga",
        "embedding_key": embedding_key,
        "group_key": group_key,
        "n_neighbors": n_neighbors,
        "root_cells": root_cells,
        "uns_key": "paga",
    }
    return adata
