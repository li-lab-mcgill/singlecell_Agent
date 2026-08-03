"""Shared utilities for multi/velocity tools."""

from __future__ import annotations

from pathlib import Path


def resolve_atac_path(adata, atac_h5ad_path) -> Path:
    """Resolve ATAC AnnData path from explicit param or adata.uns fallback.

    Raises ValueError if neither is set, FileNotFoundError if path doesn't exist.
    """
    path = atac_h5ad_path or adata.uns.get("atac_h5ad_path")
    if path is None:
        raise ValueError(
            "atac_h5ad_path not provided and adata.uns['atac_h5ad_path'] not set. "
            "Run multi_qc_intersect first to align RNA and ATAC data."
        )
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"ATAC AnnData not found: {p}")
    return p
