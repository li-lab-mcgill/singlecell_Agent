"""RNA velocity: scvelo, velocyto, UnitVelo."""

from __future__ import annotations

from typing import Any

KNOWN_METHODS = ("scvelo", "velocyto", "unitvelo")


def dispatch(adata, *, method: str, spliced_key: str = "spliced", unspliced_key: str = "unspliced", **kwargs: Any):
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown rna.rna_velocity method: {method}. Choose from {KNOWN_METHODS}.")
    raise NotImplementedError(
        f"TODO: implement rna.rna_velocity(method='{method}'). "
        "Requires spliced/unspliced layers (typically from velocyto CLI run upstream)."
    )
