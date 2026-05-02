"""RNA imputation: MAGIC, SAVER, ALRA, DCA."""

from __future__ import annotations

from typing import Any

KNOWN_METHODS = ("magic", "saver", "alra", "dca")


def dispatch(adata, *, method: str, **kwargs: Any):
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown rna.impute method: {method}. Choose from {KNOWN_METHODS}.")
    raise NotImplementedError(
        f"TODO: implement rna.impute(method='{method}'). "
        "MAGIC + DCA are Python; SAVER + ALRA require R runner."
    )
