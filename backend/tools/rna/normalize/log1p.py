"""Log-normalization: library-size normalize then log1p transform."""

from __future__ import annotations


def run(
    adata,
    *,
    target_sum: float = 1e4,
):
    import scanpy as sc

    if "counts" not in adata.layers:
        adata.layers["counts"] = adata.X.copy()
    sc.pp.normalize_total(adata, target_sum=target_sum)
    sc.pp.log1p(adata)
    adata.uns["normalization"] = {"method": "log1p", "target_sum": target_sum}
    return adata
