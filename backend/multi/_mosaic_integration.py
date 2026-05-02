"""Mosaic multimodal integration: Multigrate, StabMap, scMoMaT."""

from __future__ import annotations

from typing import Any, List

KNOWN_METHODS = ("multigrate", "stabmap", "scmomat")


def dispatch(adatas: List, modalities: List[str], *, method: str, refs=None, runners=None, **kwargs: Any):
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown multi.mosaic_integrate method: {method}. Choose from {KNOWN_METHODS}.")
    raise NotImplementedError(
        f"TODO: implement multi.mosaic_integrate(method='{method}'). "
        "Multigrate + scMoMaT are Python; StabMap via R runner."
    )
