"""Wilcoxon rank-sum differential accessibility test on ATAC peaks."""

from __future__ import annotations

from pathlib import Path

from backend.types import DEResult


def run(
    adata,
    *,
    group_key: str,
    reference: str = "rest",
    output_dir: Path | None = None,
    top_n: int = 50,
) -> DEResult:
    """Run Wilcoxon rank-sum test across ATAC peaks between cell groups.

    Args:
        adata: AnnData with peak accessibility matrix in adata.X.
        group_key: adata.obs column defining groups (e.g. "leiden").
        reference: Reference group — "rest" (default) or a specific group name.
        output_dir: If provided, saves full DA table as parquet.
        top_n: Number of top peaks to report per group.

    Returns:
        DEResult with differentially accessible peaks per group.
        Results also stored in adata.uns["rank_peaks_groups"].
    """
    import scanpy as sc
    import pandas as pd

    if group_key not in adata.obs:
        raise ValueError(f"group_key '{group_key}' not in adata.obs.")

    sc.tl.rank_genes_groups(
        adata,
        groupby=group_key,
        method="wilcoxon",
        reference=reference,
        key_added="rank_peaks_groups",
    )

    rank = adata.uns["rank_peaks_groups"]
    groups = list(rank["names"].dtype.names)
    top_per_group = {g: [str(x) for x in rank["names"][g][:top_n]] for g in groups}

    table_path = None
    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        rows = []
        for g in groups:
            for i in range(len(rank["names"][g])):
                rows.append({
                    "group": g,
                    "rank": i + 1,
                    "peak": str(rank["names"][g][i]),
                    "score": float(rank["scores"][g][i]),
                    "pval": float(rank["pvals"][g][i]) if "pvals" in rank else None,
                    "pval_adj": float(rank["pvals_adj"][g][i]) if "pvals_adj" in rank else None,
                    "lfc": float(rank["logfoldchanges"][g][i]) if "logfoldchanges" in rank else None,
                })
        table_path = output_dir / f"da_wilcoxon_{group_key}.parquet"
        pd.DataFrame(rows).to_parquet(table_path, index=False)

    return DEResult(
        method="wilcoxon",
        group_key=group_key,
        n_groups=len(groups),
        n_genes=int(adata.n_vars),
        table_path=table_path,
        top_per_group=top_per_group,
    )
