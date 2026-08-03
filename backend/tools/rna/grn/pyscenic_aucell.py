"""AUCell regulon activity scoring for pySCENIC regulons.

Scores each cell for regulon activity using the AUCell algorithm on the
regulons produced by rna_grn_pyscenic. This is the missing third stage of
the pySCENIC pipeline (grn → ctx → aucell).

Reads adata.uns["pyscenic_regulons"] ({TF: [target_genes]} dict) and produces
a cells × TF activity matrix stored in adata.obsm["X_pyscenic_auc"].
"""

from __future__ import annotations

import logging
from pathlib import Path

from backend.types import GRN

logger = logging.getLogger(__name__)


def run(
    adata,
    *,
    regulons_key: str = "pyscenic_regulons",
    auc_threshold: float = 0.05,
    n_cpu: int = 4,
    seed: int = 42,
    output_dir: Path | None = None,
) -> GRN:
    """Score each cell for TF regulon activity using AUCell (pySCENIC stage 3).

    Args:
        adata: AnnData with normalized log1p counts in adata.X.
               Must contain adata.uns[regulons_key] from rna_grn_pyscenic.
        regulons_key: adata.uns key holding the {TF: [target_genes]} regulon
                      dict produced by rna_grn_pyscenic (default 'pyscenic_regulons').
        auc_threshold: Fraction of genes in the ranking used to compute AUC
                       (default 0.05 = top 5%). Lower values are more stringent.
        n_cpu: Number of parallel workers for AUCell (default 4).
        seed: Random seed (used if AUCell sampling is required, default 42).
        output_dir: If set, saves the AUC matrix as a CSV.

    Returns:
        GRN result. AUC scores stored in:
          - adata.obsm["X_pyscenic_auc"]: cells × TF regulon activity (numpy array)
          - adata.uns["pyscenic_auc_tf_names"]: list of TF regulon names (column index)
    """
    assert regulons_key in adata.uns, (
        f"adata.uns['{regulons_key}'] not found. "
        "Run rna_grn_pyscenic first to generate regulons."
    )
    assert adata.uns[regulons_key], (
        f"adata.uns['{regulons_key}'] is empty. "
        "Check that rna_grn_pyscenic produced regulons."
    )

    return _run_aucell(
        adata,
        regulons_key=regulons_key,
        auc_threshold=auc_threshold,
        n_cpu=n_cpu,
        seed=seed,
        output_dir=Path(output_dir) if output_dir else None,
    )


def _run_aucell(
    adata,
    *,
    regulons_key,
    auc_threshold,
    n_cpu,
    seed,
    output_dir,
) -> GRN:
    import numpy as np
    import pandas as pd
    import scipy.sparse as sp

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Build expression DataFrame (cells × genes)
    X = adata.X
    if sp.issparse(X):
        X = X.toarray()
    expr_df = pd.DataFrame(X, index=adata.obs_names, columns=adata.var_names)

    # Load regulons and convert to frozenset targets
    raw_regulons = adata.uns[regulons_key]
    regulons_frozenset = {tf: frozenset(genes) for tf, genes in raw_regulons.items()}

    # Build gene rankings (cells × genes, higher expression = lower rank)
    auc_matrix = _aucell(
        expr_df=expr_df,
        regulons=regulons_frozenset,
        auc_threshold=auc_threshold,
        n_cpu=n_cpu,
        seed=seed,
    )

    # obsm stores numpy arrays, not DataFrames
    adata.obsm["X_pyscenic_auc"] = auc_matrix.values
    adata.uns["pyscenic_auc_tf_names"] = list(auc_matrix.columns)

    if output_dir is not None:
        auc_path = output_dir / "pyscenic_auc.csv"
        auc_matrix.to_csv(auc_path)
        logger.info("AUC matrix saved to %s", auc_path)

    n_tfs = auc_matrix.shape[1]
    logger.info(
        "pySCENIC AUCell complete: %d TF regulons scored across %d cells",
        n_tfs, adata.n_obs,
    )

    return GRN(
        method="pyscenic_aucell",
        n_tfs=n_tfs,
        n_targets=sum(len(g) for g in raw_regulons.values()),
        n_edges=sum(len(g) for g in raw_regulons.values()),
        metadata={
            "auc_threshold": auc_threshold,
            "regulons_key": regulons_key,
            "auc_key": "X_pyscenic_auc",
            "tf_names_key": "pyscenic_auc_tf_names",
            "n_cells": adata.n_obs,
        },
    )


def _aucell(
    expr_df: "pd.DataFrame",
    regulons: dict,
    auc_threshold: float,
    n_cpu: int,
    seed: int,
) -> "pd.DataFrame":
    """Run AUCell: rank cells by gene expression, compute AUC per regulon.

    Tries pyscenic.aucell first; falls back to manual ranking if unavailable.
    """
    try:
        from pyscenic.aucell import aucell, create_rankings
        from ctxcore.genesig import GeneSignature

        # pyscenic.aucell() expects GeneSignature objects, not a plain {str: frozenset} dict.
        # Reconstruct GeneSignature objects with uniform weight=1.0 from the stored regulon dict.
        signatures = [
            GeneSignature(name=tf, gene2weight={g: 1.0 for g in genes})
            for tf, genes in regulons.items()
        ]

        logger.info("Using pyscenic.aucell for regulon scoring")
        rankings = create_rankings(expr_df, seed=seed)
        auc_matrix = aucell(rankings, signatures, auc_threshold=auc_threshold, num_workers=n_cpu)
        return auc_matrix
    except ImportError:
        logger.info("pyscenic.aucell not available — using manual ranking fallback")
        return _aucell_manual(expr_df, regulons, auc_threshold)


def _aucell_manual(
    expr_df: "pd.DataFrame",
    regulons: dict,
    auc_threshold: float,
) -> "pd.DataFrame":
    """Manual AUCell implementation using scipy rankdata."""
    import numpy as np
    import pandas as pd
    from scipy.stats import rankdata

    n_cells, n_genes = expr_df.shape
    n_top = max(1, int(n_genes * auc_threshold))
    gene_index = {g: i for i, g in enumerate(expr_df.columns)}

    # Rank each cell: lower rank = higher expression (ascending rank, then invert)
    X = expr_df.values.astype(np.float32)
    # Dense ranks: rank 1 = lowest expression. We want rank 1 = highest.
    rankings = np.apply_along_axis(
        lambda row: (n_genes + 1) - rankdata(row, method="ordinal"), axis=1, arr=X
    )  # shape: cells × genes

    auc_records = {}
    for tf, target_genes in regulons.items():
        gene_ids = [gene_index[g] for g in target_genes if g in gene_index]
        if not gene_ids:
            auc_records[tf] = np.zeros(n_cells, dtype=np.float32)
            continue
        # AUC = (number of top-ranked targets) / (n_top * n_targets) integrated
        target_ranks = rankings[:, gene_ids]  # cells × targets
        auc_per_cell = np.array([
            _auc_from_ranks(target_ranks[i], n_genes, n_top)
            for i in range(n_cells)
        ], dtype=np.float32)
        auc_records[tf] = auc_per_cell

    return pd.DataFrame(auc_records, index=expr_df.index)


def _auc_from_ranks(ranks: "np.ndarray", n_genes: int, n_top: int) -> float:
    """Compute AUC under the recovery curve for one cell.

    AUC = (1/n_top) * sum_{k=1}^{n_top} (# target genes with rank ≤ k) / n_targets
        = sum_{i: rank_i ≤ n_top} (n_top - rank_i + 1) / (n_top * n_targets)

    Equivalent to the trapezoidal area under the recall-vs-threshold curve,
    consistent with pyscenic.aucell's scoring metric.
    """
    import numpy as np

    n_targets = len(ranks)
    if n_targets == 0 or n_top == 0:
        return 0.0
    in_top = ranks[ranks <= n_top]
    if len(in_top) == 0:
        return 0.0
    return float((n_top - in_top + 1).sum()) / (n_top * n_targets)
