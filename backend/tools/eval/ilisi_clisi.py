"""iLISI (batch mixing) and cLISI (cell type purity) metrics via scib-metrics."""

from __future__ import annotations


def run(
    adata,
    *,
    embedding_key: str,
    batch_key: str,
    label_key: str | None = None,
) -> dict:
    try:
        import scib_metrics
        return _run_scib(adata, embedding_key=embedding_key, batch_key=batch_key, label_key=label_key)
    except ImportError:
        return _run_fallback(adata, embedding_key=embedding_key, batch_key=batch_key, label_key=label_key)


def _run_scib(adata, *, embedding_key, batch_key, label_key):
    import scib_metrics

    metrics = {}
    metrics["ilisi"] = float(scib_metrics.ilisi(adata, embedding_key=embedding_key, batch_key=batch_key))
    if label_key:
        metrics["clisi"] = float(scib_metrics.clisi(adata, embedding_key=embedding_key, label_key=label_key))
    adata.uns[f"eval_lisi_{batch_key}"] = metrics
    return metrics


def _run_fallback(adata, *, embedding_key, batch_key, label_key):
    """Approximate LISI using kNN batch entropy when scib-metrics unavailable."""
    import numpy as np
    from sklearn.neighbors import NearestNeighbors

    X = adata.obsm[embedding_key]
    k = 90
    nn = NearestNeighbors(n_neighbors=min(k, adata.n_obs - 1)).fit(X)
    _, indices = nn.kneighbors(X)

    batch = adata.obs[batch_key].values
    n_batches = len(np.unique(batch))
    lisi_scores = []
    for idx_row in indices:
        neighbors_batch = batch[idx_row]
        _, counts = np.unique(neighbors_batch, return_counts=True)
        probs = counts / counts.sum()
        lisi_scores.append(1.0 / np.sum(probs ** 2))

    metrics = {"ilisi_approx": float(np.mean(lisi_scores)), "n_batches": n_batches}
    adata.uns[f"eval_lisi_{batch_key}"] = metrics
    return metrics
