"""ATAC motif enrichment: chromVAR, HOMER."""

from __future__ import annotations

from typing import Any

from ..types import MotifResult

KNOWN_METHODS = ("chromvar", "homer")


def dispatch(adata, *, motif_db: str, method: str = "chromvar", refs=None, runners=None, **kwargs: Any) -> MotifResult:
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown atac.motif_enrichment method: {method}. Choose from {KNOWN_METHODS}.")
    raise NotImplementedError(
        f"atac.motif_enrichment(method='{method}') is not implemented yet. "
        "chromVAR via R runner; HOMER via runners.cli.run(['findMotifsGenome.pl', ...]); "
        "both need refs.get_motifs(motif_db) and refs.get_genome(...)."
    )
