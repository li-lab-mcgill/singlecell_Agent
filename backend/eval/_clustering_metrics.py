"""Clustering-quality metrics: silhouette, ARI, NMI."""

from __future__ import annotations

from typing import Any, Optional


def silhouette(adata, embedding_key: str, label_key: Optional[str] = None, sample_size: int = 5000) -> float:
    """Silhouette score on an obsm embedding, labeled by label_key or a cluster column."""
    import numpy as np
    from sklearn.metrics import silhouette_score

    if embedding_key not in adata.obsm:
        raise KeyError(f"silhouette: embedding '{embedding_key}' not in adata.obsm")
    X = adata.obsm[embedding_key]
    if label_key is None or label_key not in adata.obs:
        raise KeyError("silhouette: provide a label_key or cluster column that exists in adata.obs")
    labels = adata.obs[label_key].astype(str).values
    if len(np.unique(labels)) < 2:
        return 0.0
    if X.shape[0] > sample_size:
        rng = np.random.default_rng(42)
        idx = rng.choice(X.shape[0], sample_size, replace=False)
        return float(silhouette_score(X[idx], labels[idx]))
    return float(silhouette_score(X, labels))


def ari(adata, cluster_key: str, label_key: str) -> float:
    from sklearn.metrics import adjusted_rand_score
    return float(adjusted_rand_score(adata.obs[label_key].astype(str), adata.obs[cluster_key].astype(str)))


def nmi(adata, cluster_key: str, label_key: str) -> float:
    from sklearn.metrics import normalized_mutual_info_score
    return float(normalized_mutual_info_score(adata.obs[label_key].astype(str), adata.obs[cluster_key].astype(str)))
