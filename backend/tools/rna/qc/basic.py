"""Basic RNA QC: cell filtering by gene count, mitochondrial fraction, and gene minimum cells."""

from __future__ import annotations


def run(
    adata,
    *,
    min_genes: int = 200,
    max_pct_mito: float = 20.0,
    min_cells: int = 3,
    mt_pattern: str = "^MT-",
):
    import scanpy as sc

    adata.var["mt"] = adata.var_names.str.contains(mt_pattern, regex=True)
    sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], percent_top=None, log1p=False, inplace=True)
    sc.pp.filter_cells(adata, min_genes=min_genes)
    sc.pp.filter_genes(adata, min_cells=min_cells)
    if "pct_counts_mt" in adata.obs:
        adata = adata[adata.obs["pct_counts_mt"] < max_pct_mito, :].copy()
    adata.uns["qc"] = {
        "method": "basic",
        "min_genes": min_genes,
        "max_pct_mito": max_pct_mito,
        "min_cells": min_cells,
        "n_cells_after": int(adata.n_obs),
        "n_genes_after": int(adata.n_vars),
    }
    return adata
