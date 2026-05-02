"""RNA clustering: Leiden, Louvain on a precomputed embedding."""

from __future__ import annotations

from typing import Any, Optional

KNOWN_METHODS = ("leiden", "louvain")


def dispatch(
    adata,
    *,
    embedding_key: str,
    method: str = "leiden",
    n_neighbors: int = 15,
    resolution: float = 1.0,
    cluster_key: Optional[str] = None,
    label_key: Optional[str] = None,
    **kwargs: Any,
):
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown rna.cluster method: {method}. Choose from {KNOWN_METHODS}.")
    if embedding_key not in adata.obsm:
        raise ValueError(
            f"embedding_key '{embedding_key}' not found in adata.obsm. Run rna.embed first."
        )

    import scanpy as sc

    cluster_key = cluster_key or f"{embedding_key.replace('X_', '')}_clusters"
    sc.pp.neighbors(adata, n_neighbors=n_neighbors, use_rep=embedding_key)
    if method == "leiden":
        sc.tl.leiden(adata, resolution=resolution, key_added=cluster_key)
    else:
        sc.tl.louvain(adata, resolution=resolution, key_added=cluster_key)

    metrics: dict = {"n_clusters": int(adata.obs[cluster_key].nunique())}
    if label_key and label_key in adata.obs:
        from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

        metrics["ari"] = float(adjusted_rand_score(adata.obs[label_key].astype(str), adata.obs[cluster_key].astype(str)))
        metrics["nmi"] = float(normalized_mutual_info_score(adata.obs[label_key].astype(str), adata.obs[cluster_key].astype(str)))

    adata.uns[f"{cluster_key}_metrics"] = metrics
    adata.uns["clustering"] = {
        "method": method,
        "embedding_key": embedding_key,
        "n_neighbors": n_neighbors,
        "resolution": resolution,
        "cluster_key": cluster_key,
    }
    return adata
