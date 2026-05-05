"""Clustering quality metrics: Adjusted Rand Index and Normalized Mutual Information."""

from __future__ import annotations


def run(
    adata,
    *,
    cluster_key: str,
    label_key: str,
) -> dict:
    from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score, adjusted_mutual_info_score

    if cluster_key not in adata.obs:
        raise ValueError(f"cluster_key '{cluster_key}' not found in adata.obs.")
    if label_key not in adata.obs:
        raise ValueError(f"label_key '{label_key}' not found in adata.obs.")

    labels = adata.obs[label_key].astype(str)
    clusters = adata.obs[cluster_key].astype(str)

    metrics = {
        "ari": float(adjusted_rand_score(labels, clusters)),
        "nmi": float(normalized_mutual_info_score(labels, clusters)),
        "ami": float(adjusted_mutual_info_score(labels, clusters)),
        "n_clusters": int(clusters.nunique()),
        "n_labels": int(labels.nunique()),
    }
    adata.uns[f"eval_{cluster_key}"] = metrics
    return metrics
