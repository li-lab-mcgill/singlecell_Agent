"""ATAC gene activity score: Cicero, ArchR, Signac."""

from __future__ import annotations

from typing import Any

KNOWN_METHODS = ("cicero", "archr", "signac")


def dispatch(adata, *, method: str, gene_annotation: str, refs, runners, **kwargs: Any):
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown atac.gene_activity method: {method}. Choose from {KNOWN_METHODS}.")
    raise NotImplementedError(
        f"atac.gene_activity(method='{method}') is not implemented yet. "
        "All three require R runner; gene_annotation resolves via refs.get_gtf(gene_annotation)."
    )
