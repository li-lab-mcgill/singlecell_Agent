"""Leiden graph-based clustering on a precomputed embedding."""

from __future__ import annotations


def run(
    adata,
    *,
    embedding_key: str,
    resolution: float = 1.0,
    n_neighbors: int = 15,
    cluster_key: str = "leiden_clusters",
    label_key: str | None = None,
):
    import scanpy as sc

    if embedding_key not in adata.obsm:
        raise ValueError(f"embedding_key '{embedding_key}' not found in adata.obsm. Run embed first.")

    sc.pp.neighbors(adata, n_neighbors=n_neighbors, use_rep=embedding_key)
    sc.tl.leiden(adata, resolution=resolution, key_added=cluster_key)

    metrics: dict = {"n_clusters": int(adata.obs[cluster_key].nunique())}
    if label_key and label_key in adata.obs:
        from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
        labels = adata.obs[label_key].astype(str)
        clusters = adata.obs[cluster_key].astype(str)
        metrics["ari"] = float(adjusted_rand_score(labels, clusters))
        metrics["nmi"] = float(normalized_mutual_info_score(labels, clusters))

    adata.uns[cluster_key + "_metrics"] = metrics
    adata.uns["clustering"] = {
        "method": "leiden",
        "embedding_key": embedding_key,
        "resolution": resolution,
        "n_neighbors": n_neighbors,
        "cluster_key": cluster_key,
    }
    return adata
