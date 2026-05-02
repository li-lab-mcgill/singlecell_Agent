"""Batch-correction quality: batch LISI, batch entropy, kBET.

batch_entropy is implemented directly; batch_lisi and kbet require scib /
specialized packages and are stubbed here. Fill in once you pin an
implementation choice (scib-metrics is the standard but has heavy deps).
"""

from __future__ import annotations

from typing import Any, Optional


def batch_entropy(adata, embedding_key: str, batch_key: str, n_neighbors: int = 30) -> float:
    """Mean Shannon entropy of batch labels among each cell's k nearest neighbors.

    Higher = better mixing. Max = log(n_batches).
    """
    import numpy as np
    from sklearn.neighbors import NearestNeighbors

    if embedding_key not in adata.obsm:
        raise KeyError(f"batch_entropy: embedding '{embedding_key}' not in adata.obsm")
    if batch_key not in adata.obs:
        raise KeyError(f"batch_entropy: batch '{batch_key}' not in adata.obs")

    X = adata.obsm[embedding_key]
    batches = adata.obs[batch_key].astype(str).values
    categories, labels = np.unique(batches, return_inverse=True)

    nn = NearestNeighbors(n_neighbors=n_neighbors + 1).fit(X)
    _, idx = nn.kneighbors(X)
    idx = idx[:, 1:]  # drop self

    n_cats = len(categories)
    entropies = np.zeros(X.shape[0])
    for i, neigh in enumerate(idx):
        counts = np.bincount(labels[neigh], minlength=n_cats)
        probs = counts[counts > 0] / counts.sum()
        entropies[i] = -np.sum(probs * np.log(probs))

    return float(np.mean(entropies))


def batch_lisi(adata, embedding_key: str, batch_key: str) -> float:
    raise NotImplementedError(
        "TODO: implement batch_lisi. Recommended: pip install scib-metrics, "
        "then call scib_metrics.ilisi_knn(adata.obsm[embedding_key], labels=adata.obs[batch_key])."
    )


def kbet(adata, embedding_key: str, batch_key: str) -> float:
    raise NotImplementedError(
        "TODO: implement kBET. Options: scib-metrics.kbet or an R-runner call to the kBET package."
    )
