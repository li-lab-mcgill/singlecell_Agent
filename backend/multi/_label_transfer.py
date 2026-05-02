"""Cross-dataset label transfer: scANVI, Seurat CCA, scArches, CellTypist."""

from __future__ import annotations

from typing import Any

KNOWN_METHODS = ("scanvi", "seurat_cca", "scarches", "celltypist")


def dispatch(query_adata, *, reference_atlas: str, method: str, modality: str = "rna", refs=None, runners=None, **kwargs: Any):
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown multi.label_transfer method: {method}. Choose from {KNOWN_METHODS}.")
    raise NotImplementedError(
        f"TODO: implement multi.label_transfer(method='{method}', modality='{modality}'). "
        f"Loads reference via refs.get_atlas('{reference_atlas}'). "
        "scANVI + scArches + CellTypist are Python; Seurat CCA via R runner."
    )
