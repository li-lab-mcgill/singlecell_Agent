"""ATAC clustering: Leiden / Louvain on LSI embedding (same shape as RNA clustering)."""

from __future__ import annotations

from typing import Any, Optional

KNOWN_METHODS = ("leiden", "louvain")


def dispatch(
    adata,
    *,
    embedding_key: str = "X_lsi",
    method: str = "leiden",
    resolution: float = 1.0,
    n_neighbors: int = 15,
    cluster_key: Optional[str] = None,
    **kwargs: Any,
):
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown atac.cluster method: {method}. Choose from {KNOWN_METHODS}.")
    if embedding_key not in adata.obsm:
        raise ValueError(f"embedding_key '{embedding_key}' not in adata.obsm. Run atac_tfidf_lsi first.")

    import scanpy as sc

    cluster_key = cluster_key or f"{embedding_key.replace('X_', '')}_clusters"
    sc.pp.neighbors(adata, n_neighbors=n_neighbors, use_rep=embedding_key)
    if method == "leiden":
        sc.tl.leiden(adata, resolution=resolution, key_added=cluster_key)
    else:
        sc.tl.louvain(adata, resolution=resolution, key_added=cluster_key)

    metrics = {"n_clusters": int(adata.obs[cluster_key].nunique())}
    adata.uns[f"{cluster_key}_metrics"] = metrics
    adata.uns["clustering"] = {
        "method": method,
        "embedding_key": embedding_key,
        "resolution": resolution,
        "n_neighbors": n_neighbors,
        "cluster_key": cluster_key,
        **metrics,
    }
    return adata
