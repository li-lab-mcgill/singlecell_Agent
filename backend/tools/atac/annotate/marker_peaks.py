"""ATAC cell type annotation by scoring marker peak sets per cluster."""

from __future__ import annotations


def run(
    adata,
    *,
    group_key: str,
    marker_peaks: dict[str, list[str]],
    min_score: float = 0.0,
) -> object:
    """Annotate cell clusters by scoring accessibility of known marker peak sets.

    For each cell type, computes the mean accessibility of its marker peaks
    across all clusters. Assigns the cell type with the highest score to each
    cluster, stored in adata.obs["cell_type"].

    Args:
        adata: AnnData with peak accessibility matrix. Peak names must be in
               adata.var_names (format: "chr:start-end" or any string).
        group_key: adata.obs column with cluster labels (e.g. "leiden").
        marker_peaks: Dict mapping cell type → list of marker peak names.
                      Peak names must match adata.var_names exactly.
                      Example: {"T cell": ["chr1:100-200", "chr3:500-600"]}
        min_score: Clusters with max score below this threshold are labeled
                   "Unknown" (default 0.0 — all clusters get a label).

    Returns:
        adata with adata.obs["cell_type"] and adata.obs["cell_type_score"] added.
    """
    import numpy as np
    import pandas as pd
    import scipy.sparse as sp

    if group_key not in adata.obs:
        raise ValueError(f"group_key '{group_key}' not in adata.obs.")

    # Build score matrix: clusters × cell_types
    clusters = adata.obs[group_key].unique()
    cell_types = list(marker_peaks.keys())
    scores = pd.DataFrame(index=clusters, columns=cell_types, dtype=float)

    X = adata.X
    if sp.issparse(X):
        X = X.toarray()

    var_names = list(adata.var_names)
    var_idx = {name: i for i, name in enumerate(var_names)}

    for ct, peaks in marker_peaks.items():
        # Find peaks that exist in adata
        peak_indices = [var_idx[p] for p in peaks if p in var_idx]
        if not peak_indices:
            scores[ct] = 0.0
            continue
        peak_matrix = X[:, peak_indices]  # cells × marker_peaks
        for cluster in clusters:
            mask = adata.obs[group_key] == cluster
            scores.loc[cluster, ct] = float(peak_matrix[mask].mean())

    # Assign best cell type per cluster
    best_ct = scores.idxmax(axis=1)
    best_score = scores.max(axis=1)
    best_ct[best_score < min_score] = "Unknown"

    adata.obs["cell_type"] = adata.obs[group_key].map(best_ct).astype(str)
    adata.obs["cell_type_score"] = adata.obs[group_key].map(best_score).astype(float)
    adata.uns["marker_peak_scores"] = scores.to_dict()

    return adata
