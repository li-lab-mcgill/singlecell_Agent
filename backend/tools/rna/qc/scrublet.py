"""Doublet detection using Scrublet."""

from __future__ import annotations


def run(
    adata,
    *,
    expected_doublet_rate: float = 0.06,
):
    import scanpy as sc

    sc.external.pp.scrublet(adata, expected_doublet_rate=expected_doublet_rate)
    if "predicted_doublet" in adata.obs:
        adata = adata[~adata.obs["predicted_doublet"].astype(bool), :].copy()
    adata.uns["qc_doublet"] = {
        "method": "scrublet",
        "expected_doublet_rate": expected_doublet_rate,
        "n_cells_after": int(adata.n_obs),
    }
    return adata
