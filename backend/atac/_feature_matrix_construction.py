"""ATAC feature matrix construction: peaks, tiles, bins."""

from __future__ import annotations

from typing import Any

from ._utils import peak_coordinate_schema, require_fragment_path, require_matrix

KNOWN_METHODS = ("peaks", "tiles", "bins")


def dispatch(
    adata,
    *,
    method: str,
    refs=None,
    peakset=None,
    tile_size: int = 500,
    fragments_path: str | None = None,
    **kwargs: Any,
):
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown atac.feature_matrix method: {method}. Choose from {KNOWN_METHODS}.")
    if method == "peaks":
        return _run_peaks(adata, peakset=peakset, fragments_path=fragments_path)
    require_fragment_path(fragments_path, adata=adata)
    raise NotImplementedError(
        f"atac.feature_matrix(method='{method}') requires fragment-to-bin counting and is not implemented yet."
    )


def _run_peaks(adata, *, peakset=None, fragments_path: str | None = None):
    require_matrix(adata)
    schema = peak_coordinate_schema(adata)
    if peakset is not None:
        adata.uns["peakset_path"] = str(peakset)
    adata.uns["feature_matrix"] = {
        "method": "peaks",
        "source": "existing_matrix",
        "coordinate_schema": schema["schema"],
        "n_features": int(adata.n_vars),
        "peakset": str(peakset) if peakset is not None else None,
        "fragments_path": str(fragments_path) if fragments_path is not None else getattr(adata, "uns", {}).get("fragments_path"),
    }
    return adata
