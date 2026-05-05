"""Basic ATAC QC: filter cells by count depth and feature count, filter low-coverage features."""

from __future__ import annotations


def run(
    adata,
    *,
    build: str = "hg38",
    min_counts: int = 1000,
    max_counts: int | None = 50_000,
    min_features: int = 500,
    min_cells: int = 10,
):
    import numpy as np
    from scipy import sparse
    from backend.atac._utils import require_matrix

    X = require_matrix(adata)
    X_csc = X.tocsc() if sparse.issparse(X) else sparse.csc_matrix(X)
    X_csr = X_csc.tocsr()
    cell_counts = np.asarray(X_csr.sum(axis=1)).ravel()
    # Count features per cell as non-zero columns (not stored-element count)
    cell_features = np.asarray((X_csr != 0).sum(axis=1)).ravel()

    keep_cells = cell_counts >= min_counts
    if max_counts is not None:
        keep_cells &= cell_counts <= max_counts
    keep_cells &= cell_features >= min_features
    if not bool(np.any(keep_cells)):
        raise ValueError("ATAC basic QC removed all cells; relax min_counts/max_counts/min_features.")

    adata.obs["n_counts"] = cell_counts
    adata.obs["n_features"] = cell_features
    filtered = adata[keep_cells, :].copy()

    X_filtered = filtered.X.tocsc() if sparse.issparse(filtered.X) else sparse.csc_matrix(filtered.X)
    # Count cells per feature as non-zero rows (not stored-element count)
    feature_cells = np.asarray((X_filtered != 0).sum(axis=0)).ravel()
    keep_features = feature_cells >= min_cells
    if not bool(np.any(keep_features)):
        raise ValueError("ATAC basic QC removed all features; relax min_cells.")
    filtered = filtered[:, keep_features].copy()
    filtered.var["n_cells"] = feature_cells[keep_features]
    filtered.uns["qc"] = {
        "method": "basic", "build": build,
        "min_counts": min_counts, "max_counts": max_counts,
        "min_features": min_features, "min_cells": min_cells,
        "n_cells_before": int(adata.n_obs), "n_features_before": int(adata.n_vars),
        "n_cells_after": int(filtered.n_obs), "n_features_after": int(filtered.n_vars),
    }
    return filtered
