"""Average silhouette width (ASW) for clustering quality assessment."""

from __future__ import annotations


def run(
    adata,
    *,
    cluster_key: str,
    embedding_key: str,
    subsample: int | None = 10_000,
) -> dict:
    import numpy as np
    from sklearn.metrics import silhouette_score

    if cluster_key not in adata.obs:
        raise ValueError(f"cluster_key '{cluster_key}' not found in adata.obs.")
    if embedding_key not in adata.obsm:
        raise ValueError(f"embedding_key '{embedding_key}' not found in adata.obsm.")

    X = adata.obsm[embedding_key]
    labels = adata.obs[cluster_key].astype(str).values
    n_labels = len(np.unique(labels))
    if n_labels < 2 or n_labels >= len(labels):
        raise ValueError(
            f"silhouette requires 2 to n_obs-1 clusters; found {n_labels} labels for {len(labels)} cells."
        )

    if subsample and adata.n_obs > subsample:
        idx = np.random.choice(adata.n_obs, subsample, replace=False)
        X = X[idx]
        labels = labels[idx]

    score = float(silhouette_score(X, labels, metric="euclidean"))
    metrics = {"silhouette": score, "embedding_key": embedding_key, "cluster_key": cluster_key}
    adata.uns[f"eval_silhouette_{cluster_key}"] = metrics
    return metrics
