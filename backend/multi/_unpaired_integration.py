"""Unpaired multimodal integration: scGLUE, LIGER, Seurat CCA."""

from __future__ import annotations

from typing import Any

KNOWN_METHODS = ("scglue", "liger", "seurat_cca")


def dispatch(rna_adata, atac_adata, *, method: str, refs=None, runners=None, **kwargs: Any):
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown multi.unpaired_integrate method: {method}. Choose from {KNOWN_METHODS}.")
    raise NotImplementedError(
        f"TODO: implement multi.unpaired_integrate(method='{method}'). "
        "scGLUE needs refs.get_gtf(...) for prior graph; LIGER + Seurat CCA via R runner."
    )
