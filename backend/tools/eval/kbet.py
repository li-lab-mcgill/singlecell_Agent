"""kBET (k-nearest neighbor batch effect test) for batch correction assessment."""

from __future__ import annotations


def run(
    adata,
    *,
    embedding_key: str,
    batch_key: str,
    subsample: int | None = 5_000,
) -> dict:
    if embedding_key not in adata.obsm:
        raise ValueError(f"embedding_key '{embedding_key}' not found in adata.obsm.")
    if batch_key not in adata.obs:
        raise ValueError(f"batch_key '{batch_key}' not found in adata.obs.")
    try:
        import scib_metrics
        return _run_scib(adata, embedding_key=embedding_key, batch_key=batch_key, subsample=subsample)
    except ImportError:
        return _run_fallback(adata, embedding_key=embedding_key, batch_key=batch_key, subsample=subsample)


def _run_scib(adata, *, embedding_key, batch_key, subsample):
    import scib_metrics

    score = float(scib_metrics.kbet(adata, embedding_key=embedding_key, batch_key=batch_key))
    metrics = {"kbet": score, "embedding_key": embedding_key, "batch_key": batch_key}
    adata.uns[f"eval_kbet_{batch_key}"] = metrics
    return metrics


def _run_fallback(adata, *, embedding_key, batch_key, subsample):
    """Approximate kBET as acceptance rate of chi-squared test on kNN batch composition."""
    import numpy as np
    from sklearn.neighbors import NearestNeighbors
    from scipy.stats import chi2

    X = adata.obsm[embedding_key]
    batch = adata.obs[batch_key].values
    batch_labels, batch_counts = np.unique(batch, return_counts=True)
    expected_props = batch_counts / batch_counts.sum()
    k = min(30, adata.n_obs // 10)
    if k < 1:
        raise ValueError("kBET requires at least 10 cells for the fallback kNN approximation.")

    if subsample and adata.n_obs > subsample:
        idx = np.random.choice(adata.n_obs, subsample, replace=False)
        X_sub = X[idx]
        batch_sub = batch[idx]
    else:
        X_sub, batch_sub = X, batch

    nn = NearestNeighbors(n_neighbors=k + 1).fit(X_sub)
    _, indices = nn.kneighbors(X_sub)

    accept = 0
    for i, idx_row in enumerate(indices[:, 1:]):
        neighbors_batch = batch_sub[idx_row]
        observed = np.array([np.sum(neighbors_batch == b) for b in batch_labels])
        expected = expected_props * k
        stat = np.sum((observed - expected) ** 2 / (expected + 1e-10))
        p = chi2.sf(stat, df=len(batch_labels) - 1)
        if p > 0.05:
            accept += 1

    acceptance_rate = accept / len(X_sub)
    metrics = {"kbet_acceptance_rate": float(acceptance_rate), "k": k}
    adata.uns[f"eval_kbet_{batch_key}"] = metrics
    return metrics
