"""ATAC quality control: basic filtering, TSS enrichment, fragment size, FRiP, blacklist overlap."""

from __future__ import annotations

import gzip
from typing import Any

from ._utils import require_fragment_path, require_matrix

KNOWN_METHODS = ("basic", "tss_enrichment", "fragment_size", "frip")


def dispatch(
    adata,
    *,
    method: str,
    refs=None,
    build: str = "hg38",
    min_counts: int = 1000,
    max_counts: int | None = 50_000,
    min_features: int = 500,
    min_cells: int = 10,
    fragments_path: str | None = None,
    **kwargs: Any,
):
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown atac.qc method: {method}. Choose from {KNOWN_METHODS}.")
    if method == "basic":
        return _run_basic(
            adata,
            build=build,
            min_counts=min_counts,
            max_counts=max_counts,
            min_features=min_features,
            min_cells=min_cells,
        )
    if method == "fragment_size":
        return _run_fragment_size(adata, fragments_path=fragments_path)
    if method in {"tss_enrichment", "frip"}:
        require_fragment_path(fragments_path, adata=adata)
        raise NotImplementedError(
            f"atac.qc(method='{method}') requires fragment/reference interval logic and is not implemented yet."
        )
    raise AssertionError(f"Unhandled ATAC QC method: {method}")


def _run_basic(
    adata,
    *,
    build: str,
    min_counts: int,
    max_counts: int | None,
    min_features: int,
    min_cells: int,
):
    import numpy as np
    from scipy import sparse

    X = require_matrix(adata)
    X_csr = X.tocsr() if sparse.issparse(X) else sparse.csr_matrix(X)
    cell_counts = np.asarray(X_csr.sum(axis=1)).ravel()
    cell_features = np.diff(X_csr.indptr)

    keep_cells = cell_counts >= min_counts
    if max_counts is not None:
        keep_cells &= cell_counts <= max_counts
    keep_cells &= cell_features >= min_features
    if not bool(np.any(keep_cells)):
        raise ValueError("ATAC basic QC removed all cells; relax min_counts/max_counts/min_features.")

    adata.obs["n_counts"] = cell_counts
    adata.obs["n_features"] = cell_features
    adata.obs["atac_total_counts"] = cell_counts
    adata.obs["atac_n_features"] = cell_features
    filtered = adata[keep_cells, :].copy()

    X_filtered = filtered.X.tocsc() if sparse.issparse(filtered.X) else sparse.csc_matrix(filtered.X)
    feature_cells = np.diff(X_filtered.indptr)
    keep_features = feature_cells >= min_cells
    if not bool(np.any(keep_features)):
        raise ValueError("ATAC basic QC removed all features; relax min_cells.")
    filtered = filtered[:, keep_features].copy()
    filtered.var["n_cells"] = feature_cells[keep_features]
    filtered.var["atac_n_cells"] = feature_cells[keep_features]
    filtered.uns["qc"] = {
        "method": "basic",
        "build": build,
        "min_counts": min_counts,
        "max_counts": max_counts,
        "min_features": min_features,
        "min_cells": min_cells,
        "n_cells_before": int(adata.n_obs),
        "n_features_before": int(adata.n_vars),
        "n_cells_after": int(filtered.n_obs),
        "n_features_after": int(filtered.n_vars),
    }
    return filtered


def _run_fragment_size(adata, *, fragments_path: str | None = None):
    path = require_fragment_path(fragments_path, adata=adata)
    sizes: list[int] = []
    per_barcode: dict[str, dict[str, Any]] = {}
    with _open_fragment_text(path) as handle:
        for line in handle:
            if not line or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            try:
                size = max(0, int(parts[2]) - int(parts[1]))
                count = int(parts[4]) if len(parts) >= 5 and parts[4] else 1
            except ValueError:
                continue
            if count <= 0:
                continue
            sizes.extend([size] * count)
            if len(parts) >= 4 and parts[3]:
                stats = per_barcode.setdefault(parts[3], {"count": 0, "total_size": 0, "sizes": []})
                stats["count"] += count
                stats["total_size"] += size * count
                stats["sizes"].extend([size] * count)
    if not sizes:
        raise ValueError(f"No valid fragment intervals found in {path}.")

    import numpy as np

    arr = np.asarray(sizes, dtype=float)
    adata.uns["fragment_size"] = {
        "method": "fragment_size",
        "fragments_path": str(path),
        "n_fragments": int(arr.size),
        "n_barcodes": len(per_barcode),
        "mean": float(arr.mean()),
        "median": float(np.median(arr)),
        "p95": float(np.percentile(arr, 95)),
    }
    adata.uns["qc_fragment_size"] = adata.uns["fragment_size"]
    _write_per_cell_fragment_metrics(adata, per_barcode)
    return adata


def _open_fragment_text(path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("rt", encoding="utf-8")


def _write_per_cell_fragment_metrics(adata, per_barcode: dict[str, dict[str, Any]]) -> None:
    if not per_barcode:
        return
    import numpy as np

    obs_names = [str(x) for x in getattr(adata, "obs_names", [])]
    if not obs_names and hasattr(getattr(adata, "obs", None), "index"):
        obs_names = [str(x) for x in adata.obs.index]
    if not obs_names:
        return

    counts = []
    means = []
    medians = []
    for barcode in obs_names:
        stats = per_barcode.get(barcode)
        if stats is None or stats["count"] == 0:
            counts.append(0)
            means.append(float("nan"))
            medians.append(float("nan"))
            continue
        counts.append(int(stats["count"]))
        means.append(float(stats["total_size"] / stats["count"]))
        medians.append(float(np.median(stats["sizes"])))
    adata.obs["fragment_count"] = counts
    adata.obs["fragment_size_mean"] = means
    adata.obs["fragment_size_median"] = medians
