"""RNA highly variable gene selection."""

from __future__ import annotations

from typing import Any, Optional

KNOWN_METHODS = ("seurat_v3", "cellranger", "scanpy_hvg")


def dispatch(adata, *, method: str, n_top: int = 2000, batch_key: Optional[str] = None, **kwargs: Any):
    import scanpy as sc

    flavor_map = {"seurat_v3": "seurat_v3", "cellranger": "cell_ranger", "scanpy_hvg": "seurat"}
    if method not in flavor_map:
        raise ValueError(f"Unknown rna.select_features method: {method}. Choose from {KNOWN_METHODS}.")
    kwargs: dict[str, Any] = {
        "flavor": flavor_map[method],
        "n_top_genes": n_top,
        "batch_key": batch_key,
    }
    if method == "seurat_v3" and "counts" in getattr(adata, "layers", {}):
        kwargs["layer"] = "counts"
    sc.pp.highly_variable_genes(adata, **kwargs)
    adata.uns["feature_selection"] = {"method": method, "n_top": n_top, "batch_key": batch_key}
    return adata
