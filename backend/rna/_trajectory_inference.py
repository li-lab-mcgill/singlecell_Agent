"""Trajectory inference: PAGA, Slingshot, Monocle3, Palantir."""

from __future__ import annotations

from typing import Any

KNOWN_METHODS = ("paga", "slingshot", "monocle3", "palantir")


def dispatch(adata, *, method: str, root_cells=None, **kwargs: Any):
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown rna.trajectory method: {method}. Choose from {KNOWN_METHODS}.")
    raise NotImplementedError(
        f"TODO: implement rna.trajectory(method='{method}'). "
        "PAGA + Palantir are scanpy/Python; Slingshot + Monocle3 require R runner."
    )
