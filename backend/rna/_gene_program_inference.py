"""Gene program / module inference: NMF, SCENIC, pagoda2, hotspot."""

from __future__ import annotations

from typing import Any

KNOWN_METHODS = ("nmf", "scenic", "pagoda2", "hotspot")


def dispatch(adata, *, method: str, refs=None, runners=None, n_programs: int = 20, **kwargs: Any):
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown rna.gene_programs method: {method}. Choose from {KNOWN_METHODS}.")
    raise NotImplementedError(
        f"TODO: implement rna.gene_programs(method='{method}'). "
        "SCENIC needs refs (TF motif DB + dorothea); NMF is pure Python (sklearn.decomposition.NMF); "
        "pagoda2/hotspot have R/Python implementations respectively."
    )
