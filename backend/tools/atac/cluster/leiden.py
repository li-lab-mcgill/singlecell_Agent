"""Leiden graph-based clustering on ATAC LSI or custom embedding."""

from __future__ import annotations


def run(
    adata,
    *,
    embedding_key: str = "X_lsi",
    resolution: float = 1.0,
    n_neighbors: int = 15,
    cluster_key: str = "atac_leiden_clusters",
    label_key: str | None = None,
):
    import scanpy as sc

    if embedding_key not in adata.obsm:
        raise ValueError(f"embedding_key '{embedding_key}' not found in adata.obsm.")

    sc.pp.neighbors(adata, n_neighbors=n_neighbors, use_rep=embedding_key)
    sc.tl.leiden(adata, resolution=resolution, key_added=cluster_key)

    metrics: dict = {"n_clusters": int(adata.obs[cluster_key].nunique())}
    if label_key and label_key in adata.obs:
        from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
        metrics["ari"] = float(adjusted_rand_score(adata.obs[label_key].astype(str), adata.obs[cluster_key].astype(str)))
        metrics["nmi"] = float(normalized_mutual_info_score(adata.obs[label_key].astype(str), adata.obs[cluster_key].astype(str)))

    adata.uns[cluster_key + "_metrics"] = metrics
    adata.uns["clustering"] = {
        "method": "leiden", "embedding_key": embedding_key,
        "resolution": resolution, "cluster_key": cluster_key,
    }
    return adata
