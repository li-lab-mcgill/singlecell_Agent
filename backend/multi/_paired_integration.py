"""Paired multimodal integration: WNN, MultiVI, Cobolt, scGLUE."""

from __future__ import annotations

from typing import Any

KNOWN_METHODS = ("wnn", "multivi", "cobolt", "scglue")


def dispatch(rna_adata, atac_adata, *, method: str, refs=None, runners=None, batch_key=None, **kwargs: Any):
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown multi.paired_integrate method: {method}. Choose from {KNOWN_METHODS}.")
    raise NotImplementedError(
        f"TODO: implement multi.paired_integrate(method='{method}'). "
        "WNN via Seurat (R runner); MultiVI uses scvi-tools; Cobolt + scGLUE are Python."
    )
