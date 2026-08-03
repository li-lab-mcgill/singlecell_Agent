"""KNN chromatin smoothing for MultiVelo using the WNN neighbor graph.

Smooths raw gene-level ATAC accessibility using the KNN graph from multi_embed_wnn.
Required before multi_velocity_recover_dynamics because raw peak aggregation produces
sparse, noisy chromatin signals.

Reuses the existing WNN neighbor graph — no new graph is computed here.

IMPORTANT: Uses sparse-aware row-by-row extraction from adata.obsp["distances"].
Do NOT call .toarray() — that materializes an (n_cells × n_cells) dense matrix
which will OOM on any real dataset (50k cells ≈ 20 GB).
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def run(
    adata,
    *,
    atac_h5ad_path: str | Path | None = None,
    n_neighbors: int | None = None,
    output_dir: Path | None = None,
) -> object:
    """Smooth chromatin accessibility using KNN neighbors from the WNN graph.

    Args:
        adata: RNA AnnData. Must have adata.obsp["distances"] (from multi_embed_wnn
               or sc.pp.neighbors) and adata.uns["atac_h5ad_path"].
        atac_h5ad_path: Path to gene-level ATAC AnnData with Mc layer (from
                        multi_velocity_aggregate_peaks). Falls back to
                        adata.uns["atac_h5ad_path"].
        n_neighbors: Number of neighbors for smoothing. If None, inferred in
                     priority order: adata.uns["wnn"]["n_neighbors"] →
                     adata.uns["neighbors"]["params"]["n_neighbors"]. Pass
                     explicitly to override.
        output_dir: Unused (reserved). ATAC adata is saved back to atac_h5ad_path.

    Returns:
        adata with adata.uns["velocity_knn_smooth"] written.
        ATAC adata is updated in-place and saved back to its path.
    """
    if "distances" not in adata.obsp:
        raise ValueError(
            "adata.obsp['distances'] not found. "
            "Run multi_embed_wnn (or sc.pp.neighbors) first to build a neighbor graph."
        )

    atac_path = _resolve_atac_path(adata, atac_h5ad_path)

    k = _resolve_n_neighbors(adata, n_neighbors)
    logger.info("Using k=%d neighbors for KNN chromatin smoothing", k)

    return _run_knn_smooth(adata, atac_path=atac_path, k=k)


from backend.tools.multi.velocity._utils import resolve_atac_path as _resolve_atac_path


def _resolve_n_neighbors(adata, n_neighbors) -> int:
    k = (
        n_neighbors
        or adata.uns.get("wnn", {}).get("n_neighbors")
        or adata.uns.get("neighbors", {}).get("params", {}).get("n_neighbors")
    )
    if k is None:
        raise ValueError(
            "Could not determine n_neighbors. Run multi_embed_wnn first "
            "or pass n_neighbors explicitly."
        )
    return int(k)


def _extract_knn_from_sparse(D, k: int):
    """Sparse-aware extraction of nn_idx and nn_dist from a CSR distances matrix.

    D is sparse CSR where only the k actual neighbors have nonzero entries.
    DO NOT call .toarray() — materializes a dense (n_cells × n_cells) matrix.
    """
    n_cells = D.shape[0]
    nn_idx = np.zeros((n_cells, k), dtype=int)
    nn_dist = np.zeros((n_cells, k), dtype=float)

    for i in range(n_cells):
        row = D.getrow(i)
        nz_idx = row.indices      # column indices of actual neighbors
        nz_dist = row.data        # their distances
        order = np.argsort(nz_dist)[:k]
        n = len(order)
        nn_idx[i, :n] = nz_idx[order]
        nn_dist[i, :n] = nz_dist[order]
        # Pad remaining slots with self-loop (distance 0) rather than cell 0,
        # to avoid phantom neighbor artifact for boundary cells with < k neighbors
        if n < k:
            nn_idx[i, n:] = i
            nn_dist[i, n:] = 0.0

    return nn_idx, nn_dist


def _run_knn_smooth(adata, *, atac_path, k):
    import anndata as ad
    import multivelo as mv

    adata_atac = ad.read_h5ad(atac_path)

    if "Mc" not in adata_atac.layers:
        raise ValueError(
            "adata_atac.layers['Mc'] not found. "
            "Run multi_velocity_aggregate_peaks first to compute TF-IDF normalized "
            "gene-level accessibility."
        )

    logger.info(
        "Extracting KNN indices from sparse distances matrix (%d cells)", adata.n_obs
    )
    D = adata.obsp["distances"]
    nn_idx, nn_dist = _extract_knn_from_sparse(D, k)

    logger.info("Smoothing chromatin accessibility with KNN (k=%d)", k)
    mv.knn_smooth_chrom(adata_atac, nn_idx, nn_dist)

    adata_atac.write_h5ad(atac_path)
    logger.info("Smoothed ATAC adata saved back to %s", atac_path)

    source = "wnn" if "wnn" in adata.uns else "neighbors"
    adata.uns["velocity_knn_smooth"] = {
        "n_neighbors": k,
        "source": source,
    }

    return adata
