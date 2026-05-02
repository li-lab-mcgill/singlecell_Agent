"""Joint RNA velocity using ATAC priors: MultiVelo, UnitVelo-multi."""

from __future__ import annotations

from typing import Any

KNOWN_METHODS = ("multivelo", "unitvelo_multi")


def dispatch(rna_adata, atac_adata, *, method: str, **kwargs: Any):
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown multi.joint_rna_velocity method: {method}. Choose from {KNOWN_METHODS}.")
    raise NotImplementedError(
        f"TODO: implement multi.joint_rna_velocity(method='{method}'). Both are Python; require spliced/unspliced + chromatin layers."
    )
