"""RNA quality control: cell filtering, doublet detection, ambient RNA removal."""

from __future__ import annotations

from typing import Any, Optional

KNOWN_METHODS = ("basic", "scrublet", "scdblfinder", "soupx", "cellbender", "emptydrops")


def dispatch(
    adata,
    *,
    method: str,
    runners: Optional[Any] = None,
    min_genes: int = 200,
    max_pct_mito: float = 20.0,
    min_cells: int = 3,
    mt_pattern: str = "^MT-",
    expected_doublet_rate: float = 0.06,
    **kwargs: Any,
):
    if method == "basic":
        return _run_basic(adata, min_genes=min_genes, max_pct_mito=max_pct_mito, min_cells=min_cells, mt_pattern=mt_pattern)
    if method == "scrublet":
        return _run_scrublet(adata, expected_doublet_rate=expected_doublet_rate, **kwargs)
    if method == "scdblfinder":
        return _run_scdblfinder(adata, runners=runners, **kwargs)
    if method == "soupx":
        return _run_soupx(adata, runners=runners, **kwargs)
    if method == "cellbender":
        return _run_cellbender(adata, **kwargs)
    if method == "emptydrops":
        return _run_emptydrops(adata, runners=runners, **kwargs)
    raise ValueError(f"Unknown rna.qc method: {method}. Choose from {KNOWN_METHODS}.")


# ----------------------------------------------------------------------
# Implemented
# ----------------------------------------------------------------------

def _run_basic(adata, *, min_genes: int, max_pct_mito: float, min_cells: int, mt_pattern: str):
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


def _run_scrublet(adata, *, expected_doublet_rate: float, **_: Any):
    import scanpy as sc

    sc.external.pp.scrublet(adata, expected_doublet_rate=expected_doublet_rate)
    if "predicted_doublet" in adata.obs:
        adata = adata[~adata.obs["predicted_doublet"].astype(bool), :].copy()
    adata.uns["qc_doublet"] = {"method": "scrublet", "expected_doublet_rate": expected_doublet_rate}
    return adata


# ----------------------------------------------------------------------
# Stubs
# ----------------------------------------------------------------------

def _run_scdblfinder(adata, *, runners, **_: Any):
    raise NotImplementedError("TODO: implement scDblFinder via R runner (r_scripts/rna/doublet_scdblfinder.R)")


def _run_soupx(adata, *, runners, **_: Any):
    raise NotImplementedError("TODO: implement SoupX via R runner (r_scripts/rna/ambient_soupx.R)")


def _run_cellbender(adata, **_: Any):
    raise NotImplementedError("TODO: implement CellBender (subprocess CLI: cellbender remove-background)")


def _run_emptydrops(adata, *, runners, **_: Any):
    raise NotImplementedError("TODO: implement emptyDrops via R runner (r_scripts/rna/empty_drops.R)")
