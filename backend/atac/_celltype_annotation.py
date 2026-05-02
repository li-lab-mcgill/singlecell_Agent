"""ATAC cell type annotation: RNA label transfer, marker peaks."""

from __future__ import annotations

from typing import Any

from ._utils import parse_peak_coordinates, require_matrix

KNOWN_METHODS = ("rna_label_transfer", "marker_peaks")


def dispatch(adata, *, method: str, refs=None, runners=None, reference_atlas: str | None = None, **kwargs: Any):
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown atac.annotate method: {method}. Choose from {KNOWN_METHODS}.")
    if method == "marker_peaks":
        return _run_marker_peaks(adata, refs=refs, **kwargs)
    raise NotImplementedError(
        f"atac.annotate(method='{method}') is not implemented yet. "
        "rna_label_transfer typically uses Signac/Seurat via R runner OR scGLUE pairing; "
        "marker_peaks uses a peak-set DB (like TF motif / known marker peak panels)."
    )


def _run_marker_peaks(
    adata,
    *,
    group_key: str,
    marker_peak_sets: dict[str, list[str]] | None = None,
    annotation_key: str | None = None,
    min_markers: int = 1,
    refs=None,
    **_: Any,
):
    import numpy as np
    from scipy import sparse

    X = require_matrix(adata)
    peaks = parse_peak_coordinates(adata)
    if group_key not in getattr(adata, "obs", {}):
        raise ValueError(f"group_key '{group_key}' not found in adata.obs.")
    if min_markers <= 0:
        raise ValueError("min_markers must be positive.")

    marker_peak_sets = marker_peak_sets or getattr(adata, "uns", {}).get("marker_peak_sets")
    if not marker_peak_sets:
        raise ValueError("marker_peaks requires marker_peak_sets or adata.uns['marker_peak_sets'].")

    peak_to_index = _peak_index(peaks)
    resolved_sets: dict[str, list[int]] = {}
    missing_sets: dict[str, list[str]] = {}
    for cell_type, markers in marker_peak_sets.items():
        indices = []
        missing = []
        for marker in markers:
            matched = _marker_indices(marker, peaks, peak_to_index)
            if not matched:
                missing.append(str(marker))
            else:
                indices.extend(matched)
        if len(indices) >= min_markers:
            resolved_sets[str(cell_type)] = sorted(set(indices))
        missing_sets[str(cell_type)] = missing
    if not resolved_sets:
        raise ValueError("No marker peak set had enough peaks present in adata.var_names/coordinates.")

    groups = _series_as_strings(getattr(adata, "obs")[group_key])
    unique_groups = sorted(set(groups))
    matrix = X.tocsr() if sparse.issparse(X) else np.asarray(X)
    cluster_to_celltype: dict[str, str] = {}
    cluster_scores: dict[str, dict[str, float]] = {}
    for group in unique_groups:
        mask = np.asarray([value == group for value in groups])
        if not mask.any():
            continue
        scores = {}
        for cell_type, indices in resolved_sets.items():
            values = matrix[mask][:, indices]
            if sparse.issparse(values):
                values = values.copy()
                values.data[:] = 1
                scores[cell_type] = float(values.mean())
            else:
                scores[cell_type] = float((values > 0).mean())
        best = max(scores, key=scores.get)
        cluster_to_celltype[group] = best if scores[best] > 0 else "Unknown"
        cluster_scores[group] = scores

    output_key = annotation_key or f"{group_key}_celltype"
    labels = [cluster_to_celltype.get(group, "Unknown") for group in groups]
    getattr(adata, "obs")[output_key] = labels
    adata.uns["annotation"] = {
        "method": "marker_peaks",
        "group_key": group_key,
        "annotation_key": output_key,
        "cluster_to_celltype": cluster_to_celltype,
        "cluster_scores": cluster_scores,
        "n_marker_sets": len(marker_peak_sets),
        "n_resolved_marker_sets": len(resolved_sets),
        "missing_marker_peaks": missing_sets,
    }
    return adata


def _peak_index(peaks: list[tuple[str, int, int, str]]) -> dict[str, int]:
    result = {}
    for index, (chrom, start, end, name) in enumerate(peaks):
        result[str(name)] = index
        result[f"{chrom}:{start}-{end}"] = index
    return result


def _marker_indices(marker: Any, peaks: list[tuple[str, int, int, str]], peak_to_index: dict[str, int]) -> list[int]:
    parsed = _parse_marker_interval(marker)
    if parsed is None:
        index = peak_to_index.get(str(marker))
        return [] if index is None else [index]
    chrom, start, end = parsed
    return [
        index
        for index, (peak_chrom, peak_start, peak_end, _name) in enumerate(peaks)
        if peak_chrom == chrom and peak_start < end and peak_end > start
    ]


def _parse_marker_interval(marker: Any) -> tuple[str, int, int] | None:
    if isinstance(marker, dict):
        chrom = marker.get("chrom") or marker.get("chr")
        start = marker.get("start")
        end = marker.get("end")
        if chrom is None or start is None or end is None:
            return None
        return str(chrom), int(start), int(end)
    text = str(marker)
    if ":" not in text or "-" not in text:
        return None
    chrom, rest = text.split(":", 1)
    start, end = rest.split("-", 1)
    try:
        return chrom, int(start.replace(",", "")), int(end.replace(",", ""))
    except ValueError:
        return None


def _series_as_strings(values: Any) -> list[str]:
    if hasattr(values, "astype"):
        try:
            return [str(value) for value in values.astype(str)]
        except Exception:
            pass
    return [str(value) for value in values]
