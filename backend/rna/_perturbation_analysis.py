"""Perturbation analysis: Mixscape, GEARS, CPA."""

from __future__ import annotations

from typing import Any

KNOWN_METHODS = ("mixscape", "gears", "cpa")


def dispatch(adata, *, method: str, perturbation_key: str, **kwargs: Any):
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown rna.perturbation method: {method}. Choose from {KNOWN_METHODS}.")
    raise NotImplementedError(
        f"TODO: implement rna.perturbation(method='{method}'). "
        f"perturbation_key='{perturbation_key}'. Mixscape lives in pertpy/Seurat; GEARS + CPA are pure Python."
    )
