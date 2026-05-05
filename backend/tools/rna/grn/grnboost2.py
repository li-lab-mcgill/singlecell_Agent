"""Standalone GRNBoost2 co-expression GRN inference via arboreto.

Infers TF → gene importance scores using gradient-boosted trees on expression data.
Produces a weighted adjacency matrix without any motif pruning step.

For full regulon inference (co-expression + motif validation), use rna_grn_pyscenic.
"""

from __future__ import annotations

from pathlib import Path

from backend.types import GRN


def run(
    adata,
    *,
    tf_list_path: str | Path | None = None,
    n_jobs: int = 4,
    seed: int = 42,
    output_dir: Path | None = None,
) -> GRN:
    """Run GRNBoost2 to infer a TF→gene co-expression adjacency matrix.

    Args:
        adata: AnnData with normalized log1p counts in adata.X.
        tf_list_path: Path to a text file with one TF name per line.
                      If None, all genes are treated as potential TFs (much slower).
        n_jobs: Number of parallel workers (default 4).
        seed: Random seed for reproducibility (default 42).
        output_dir: If provided, saves adjacency matrix as parquet.

    Returns:
        GRN result. Adjacency matrix also stored in adata.uns["grnboost2_adjacencies"]
        as a list of {TF, target, importance} dicts.
    """
    return _run_grnboost2(
        adata,
        tf_list_path=Path(tf_list_path) if tf_list_path else None,
        n_jobs=n_jobs,
        seed=seed,
        output_dir=Path(output_dir) if output_dir else None,
    )


def _run_grnboost2(adata, *, tf_list_path, n_jobs, seed, output_dir) -> GRN:
    import pandas as pd
    import scipy.sparse as sp
    from arboreto.algo import grnboost2
    from arboreto.utils import load_tf_names

    # Build expression DataFrame (cells × genes)
    X = adata.X
    if sp.issparse(X):
        X = X.toarray()
    expr_df = pd.DataFrame(X, index=adata.obs_names, columns=adata.var_names)

    # Load and filter TF list
    tf_names = None
    if tf_list_path is not None:
        tf_names = load_tf_names(str(tf_list_path))
        tf_names = [t for t in tf_names if t in adata.var_names]
        if not tf_names:
            raise ValueError(
                f"None of the TFs in '{tf_list_path}' were found in adata.var_names. "
                "Check that gene names match (symbol vs Ensembl ID)."
            )

    adjacencies = grnboost2(
        expression_data=expr_df,
        tf_names=tf_names,
        verbose=False,
        seed=seed,
    )
    # adjacencies: DataFrame [TF, target, importance]

    # Store in adata for downstream use (e.g. pySCENIC ctx step)
    adata.uns["grnboost2_adjacencies"] = adjacencies.to_dict("records")

    adj_path = None
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        adj_path = output_dir / "grnboost2_adjacencies.parquet"
        adjacencies.to_parquet(adj_path, index=False)

    n_tfs = int(adjacencies["TF"].nunique())
    n_targets = int(adjacencies["target"].nunique())
    n_edges = len(adjacencies)

    return GRN(
        method="grnboost2",
        n_tfs=n_tfs,
        n_targets=n_targets,
        n_edges=n_edges,
        edges_path=adj_path,
        metadata={
            "tf_list_path": str(tf_list_path) if tf_list_path else "all_genes",
            "n_tfs_used": n_tfs,
            "adjacencies_key": "grnboost2_adjacencies",
            "note": "Co-expression only — no motif pruning. For regulons use rna_grn_pyscenic.",
        },
    )
