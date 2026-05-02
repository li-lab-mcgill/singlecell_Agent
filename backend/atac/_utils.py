"""Shared helpers for ATAC matrix and coordinate methods."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional


_PEAK_RE = re.compile(r"^(?P<chrom>[^:\s]+):(?P<start>\d+)-(?P<end>\d+)$")


def require_fragment_path(fragments_path: str | Path | None, adata: Any = None) -> Path:
    candidate = fragments_path
    if candidate is None and adata is not None:
        candidate = getattr(adata, "uns", {}).get("fragments_path")
    if candidate is None:
        raise ValueError("This ATAC method requires fragments_path or adata.uns['fragments_path'].")
    path = Path(candidate)
    if not path.is_file():
        raise FileNotFoundError(f"fragments_path does not exist or is not a file: {path}")
    return path


def peak_coordinate_schema(adata: Any) -> dict[str, Any]:
    """Validate and describe peak coordinates on adata.var.

    Accepts either explicit var columns (chrom/start/end) or var_names formatted
    as chr:start-end. Raises ValueError if no valid schema is found.
    """

    var = getattr(adata, "var", None)
    columns = _columns(var)
    if {"chrom", "start", "end"}.issubset(columns):
        chrom = [str(x) for x in var["chrom"]]
        start = [int(x) for x in var["start"]]
        end = [int(x) for x in var["end"]]
        _validate_coordinate_vectors(chrom, start, end)
        return {"schema": "var_columns", "n_peaks": len(chrom)}

    var_names = [str(x) for x in getattr(adata, "var_names", [])]
    if var_names:
        parsed = [_PEAK_RE.match(name) for name in var_names]
        if all(match is not None for match in parsed):
            chrom = [match.group("chrom") for match in parsed if match is not None]
            start = [int(match.group("start")) for match in parsed if match is not None]
            end = [int(match.group("end")) for match in parsed if match is not None]
            _validate_coordinate_vectors(chrom, start, end)
            return {"schema": "var_names_chr_start_end", "n_peaks": len(var_names)}

    raise ValueError(
        "ATAC peak coordinates are required. Provide adata.var columns chrom/start/end "
        "or var_names formatted as 'chr:start-end'."
    )


def parse_peak_coordinates(adata: Any) -> list[tuple[str, int, int, str]]:
    peak_coordinate_schema(adata)
    var = getattr(adata, "var", None)
    columns = _columns(var)
    if {"chrom", "start", "end"}.issubset(columns):
        names = [str(x) for x in getattr(adata, "var_names", [])]
        chrom = [str(x) for x in var["chrom"]]
        start = [int(x) for x in var["start"]]
        end = [int(x) for x in var["end"]]
        return [(c, s, e, names[i] if i < len(names) else f"{c}:{s}-{e}") for i, (c, s, e) in enumerate(zip(chrom, start, end))]

    peaks = []
    for name in [str(x) for x in getattr(adata, "var_names", [])]:
        match = _PEAK_RE.match(name)
        if match is None:
            raise ValueError(f"Invalid peak coordinate: {name}")
        peaks.append((match.group("chrom"), int(match.group("start")), int(match.group("end")), name))
    return peaks


def _validate_coordinate_vectors(chrom: list[str], start: list[int], end: list[int]) -> None:
    if not (len(chrom) == len(start) == len(end)):
        raise ValueError("Peak coordinate columns must have matching lengths.")
    bad = [
        f"{c}:{s}-{e}"
        for c, s, e in zip(chrom[:20], start[:20], end[:20])
        if not c or s < 0 or e <= s
    ]
    if bad:
        raise ValueError(f"Invalid peak coordinates found: {bad[:5]}")


def _columns(frame: Any) -> set[str]:
    if frame is None:
        return set()
    columns = getattr(frame, "columns", None)
    if columns is not None:
        return {str(column) for column in columns}
    if isinstance(frame, dict):
        return {str(column) for column in frame.keys()}
    if hasattr(frame, "keys"):
        try:
            return {str(column) for column in frame.keys()}
        except Exception:
            return set()
    return set()


def require_matrix(adata: Any) -> Any:
    matrix = getattr(adata, "X", None)
    if matrix is None:
        raise ValueError("ATAC method requires adata.X to contain a cell x feature matrix.")
    shape = getattr(matrix, "shape", getattr(adata, "shape", None))
    if shape is None or len(shape) != 2 or shape[0] == 0 or shape[1] == 0:
        raise ValueError(f"ATAC method requires a non-empty 2D matrix; got shape={shape}.")
    return matrix


def optional_output_dir(output_dir: str | Path | None) -> Optional[Path]:
    if output_dir is None:
        return None
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path
