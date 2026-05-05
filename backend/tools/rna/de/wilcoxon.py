"""Wilcoxon rank-sum differential expression test."""

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
):
    return _run_scanpy_de(adata, group_key=group_key, method="wilcoxon",
                          reference=reference, output_dir=output_dir, top_n=top_n)


def _run_scanpy_de(adata, *, group_key, method, reference, output_dir, top_n) -> DEResult:
    import scanpy as sc

    if group_key not in adata.obs:
        raise ValueError(f"group_key '{group_key}' not in adata.obs.")

    method_map = {"wilcoxon": "wilcoxon", "t": "t-test", "logreg": "logreg"}
    sc.tl.rank_genes_groups(adata, groupby=group_key, method=method_map[method], reference=reference)
    rank = adata.uns["rank_genes_groups"]
    groups = list(rank["names"].dtype.names)
    top_per_group = {g: [str(x) for x in rank["names"][g][:top_n]] for g in groups}

    table_path = None
    if output_dir is not None:
        import pandas as pd
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        rows = []
        for g in groups:
            for i in range(len(rank["names"][g])):
                rows.append({
                    "group": g, "rank": i + 1,
                    "gene": str(rank["names"][g][i]),
                    "score": float(rank["scores"][g][i]),
                    "pval": float(rank["pvals"][g][i]) if "pvals" in rank else None,
                    "pval_adj": float(rank["pvals_adj"][g][i]) if "pvals_adj" in rank else None,
                    "lfc": float(rank["logfoldchanges"][g][i]) if "logfoldchanges" in rank else None,
                })
        table_path = output_dir / f"de_{method}_{group_key}.parquet"
        pd.DataFrame(rows).to_parquet(table_path, index=False)

    return DEResult(method=method, group_key=group_key, n_groups=len(groups),
                    n_genes=int(adata.n_vars), table_path=table_path, top_per_group=top_per_group)
