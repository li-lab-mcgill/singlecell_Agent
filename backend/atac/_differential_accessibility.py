"""ATAC differential accessibility: wilcoxon, logreg, edgeR/DESeq2 pseudobulk."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..types import DEResult
from ._utils import optional_output_dir, peak_coordinate_schema, require_matrix

KNOWN_METHODS = ("wilcoxon", "logreg", "edger_pseudobulk", "deseq2_pseudobulk")


def dispatch(
    adata,
    *,
    group_key: str,
    method: str = "wilcoxon",
    runners=None,
    output_dir: str | Path | None = None,
    top_n: int = 50,
    binarize: bool = True,
    **kwargs: Any,
) -> DEResult:
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown atac.differential_accessibility method: {method}. Choose from {KNOWN_METHODS}.")
    if group_key not in adata.obs:
        raise ValueError(f"group_key '{group_key}' not found in adata.obs.")
    if method in {"wilcoxon", "logreg"}:
        return _run_scanpy_da(
            adata,
            group_key=group_key,
            method=method,
            output_dir=output_dir,
            top_n=top_n,
            binarize=binarize,
        )
    raise NotImplementedError(
        f"atac.differential_accessibility(method='{method}') is not implemented yet. "
        "Condition-level DA should use replicate-aware pseudobulk with sample_key."
    )


def _run_scanpy_da(
    adata,
    *,
    group_key: str,
    method: str,
    output_dir: str | Path | None,
    top_n: int,
    binarize: bool,
) -> DEResult:
    import math

    import scanpy as sc
    from scipy import sparse

    method_map = {"wilcoxon": "wilcoxon", "logreg": "logreg"}
    coordinate_schema = peak_coordinate_schema(adata)
    require_matrix(adata)

    work = adata.copy() if binarize else adata
    if binarize:
        X = require_matrix(work)
        if sparse.issparse(X):
            X = X.copy()
            X.data[:] = 1
            work.X = X
        else:
            work.X = (X > 0).astype(float)

    sc.tl.rank_genes_groups(work, groupby=group_key, method=method_map[method], use_raw=False)
    rank = work.uns["rank_genes_groups"]
    adata.uns["rank_genes_groups"] = rank
    groups = list(rank["names"].dtype.names)
    top_per_group = {group: [str(x) for x in rank["names"][group][:top_n]] for group in groups}

    table_path = None
    outdir = optional_output_dir(output_dir)
    if outdir is not None:
        import pandas as pd

        rows = []
        for group in groups:
            names = rank["names"][group]
            for idx, peak in enumerate(names):
                row = {
                    "group": group,
                    "rank": idx + 1,
                    "peak": str(peak),
                    "score": _safe_float(_rank_value(rank, "scores", group, idx)),
                    "pval": _safe_float(_rank_value(rank, "pvals", group, idx)),
                    "pval_adj": _safe_float(_rank_value(rank, "pvals_adj", group, idx)),
                    "lfc": _safe_float(_rank_value(rank, "logfoldchanges", group, idx)),
                }
                rows.append(row)
        table_path = outdir / f"da_{method}_{group_key}.csv"
        pd.DataFrame(rows).to_csv(table_path, index=False)

    adata.uns["differential_accessibility"] = {
        "method": method,
        "group_key": group_key,
        "n_groups": len(groups),
        "top_n": top_n,
        "binarize": binarize,
        "coordinate_schema": coordinate_schema,
    }
    return DEResult(
        method=method,
        group_key=group_key,
        n_groups=len(groups),
        n_genes=int(adata.n_vars),
        table_path=table_path,
        top_per_group=top_per_group,
        metrics={"coordinate_schema": coordinate_schema, "exploratory": True, "binarize": binarize},
    )


def _safe_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(result):
        return None
    return result


def _rank_value(rank: dict[str, Any], key: str, group: str, idx: int) -> Any:
    if key not in rank:
        return None
    try:
        return rank[key][group][idx]
    except Exception:
        return None
