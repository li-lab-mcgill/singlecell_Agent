"""Workspace Profiler — describes all data files in the workspace.

Reads structural facts from each file (h5ad, csv, tsv, loom, etc.) and merges
them with user-provided biological context. The LLM downstream interprets what
each column means — the profiler only reports what is there.

Usage:
    from backend.workspace_profiler import profile_workspace

    # Single file
    profile = profile_workspace("data/pbmc.h5ad", user_context={...})

    # Multiple files (RNA + ATAC + metadata)
    profile = profile_workspace(
        ["data/rna.h5ad", "data/atac.h5ad", "data/metadata.csv"],
        user_context={"tissue": "PBMC", "disease": "AD", "modality": "multiome"},
    )

    # Directory — scans for all supported files
    profile = profile_workspace("data/", user_context={...})
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


_SUPPORTED_EXTENSIONS = {".h5ad", ".h5", ".loom", ".csv", ".tsv", ".txt"}
_QC_COLUMNS = {
    "n_genes_by_counts", "total_counts", "total_counts_mt",
    "pct_counts_mt", "log1p_n_genes_by_counts", "log1p_total_counts",
    "pct_counts_in_top_50_genes", "pct_counts_in_top_200_genes",
    "pct_counts_in_top_500_genes",
}


# ---------------------------------------------------------------------------
# Per-format profilers
# ---------------------------------------------------------------------------

def _profile_obs_columns(obs) -> dict[str, Any]:
    """Return per-column structural facts from a pandas DataFrame (adata.obs or csv)."""
    result = {}
    for col in obs.columns:
        series = obs[col]
        dtype_name = series.dtype.name

        if dtype_name in ("category", "object"):
            try:
                n_unique = int(series.nunique())
                examples = [str(v) for v in series.dropna().unique()[:8].tolist()]
            except Exception:
                n_unique = -1
                examples = []
            result[col] = {"dtype": "categorical", "n_unique": n_unique, "values": examples}

        elif "float" in dtype_name or "int" in dtype_name:
            try:
                result[col] = {
                    "dtype": "numeric",
                    "min": round(float(series.min()), 4),
                    "max": round(float(series.max()), 4),
                    "mean": round(float(series.mean()), 4),
                }
            except Exception:
                result[col] = {"dtype": dtype_name}
        else:
            result[col] = {"dtype": dtype_name}
    return result


def _check_x_matrix(x, n_obs: int) -> dict[str, Any]:
    """Heuristically determine whether X looks like raw counts."""
    import numpy as np

    try:
        import scipy.sparse as sp
        is_sparse = sp.issparse(x)
    except ImportError:
        is_sparse = False

    try:
        n_sample = min(200, n_obs)
        if is_sparse:
            sample = np.array(x[:n_sample].toarray(), dtype=float)
        else:
            sample = np.array(x[:n_sample], dtype=float)
        looks_integer = bool(np.allclose(sample, np.round(sample), atol=1e-3))
        has_negatives = bool((sample < 0).any())
        likely_raw = looks_integer and not has_negatives
    except Exception:
        likely_raw = False if "float" in str(x.dtype) else None

    return {
        "dtype": str(x.dtype),
        "sparse": is_sparse,
        "likely_raw_counts": likely_raw,
    }


def _profile_h5ad(path: Path) -> dict[str, Any]:
    import anndata
    adata = anndata.read_h5ad(path, backed="r")

    profile: dict[str, Any] = {
        "filename": path.name,
        "path": str(path),
        "format": "h5ad",
        "n_cells": adata.n_obs,
        "n_genes": adata.n_vars,
        "obs_columns": _profile_obs_columns(adata.obs),
        "var_columns": list(adata.var.columns),
        "layers": list(adata.layers.keys()),
        "obsm_keys": list(adata.obsm.keys()),
        "uns_keys": list(adata.uns.keys()),
        "x_matrix": _check_x_matrix(adata.X, adata.n_obs),
    }

    if hasattr(adata, "file") and adata.file is not None:
        try:
            adata.file.close()
        except Exception:
            pass

    return profile


def _profile_loom(path: Path) -> dict[str, Any]:
    try:
        import loompy
        with loompy.connect(str(path), mode="r") as ds:
            return {
                "filename": path.name,
                "path": str(path),
                "format": "loom",
                "n_cells": ds.shape[1],
                "n_genes": ds.shape[0],
                "col_attrs": list(ds.col_attrs.keys()),
                "row_attrs": list(ds.row_attrs.keys()),
                "layers": list(ds.layers.keys()),
            }
    except Exception as exc:
        return {"filename": path.name, "path": str(path), "format": "loom", "error": str(exc)}


def _profile_tabular(path: Path) -> dict[str, Any]:
    try:
        import pandas as pd
        sep = "\t" if path.suffix in (".tsv", ".txt") else ","
        df = pd.read_csv(path, sep=sep, nrows=5000)
        return {
            "filename": path.name,
            "path": str(path),
            "format": path.suffix.lstrip("."),
            "n_rows": len(df),
            "columns": _profile_obs_columns(df),
        }
    except Exception as exc:
        return {"filename": path.name, "path": str(path), "format": path.suffix.lstrip("."), "error": str(exc)}


def _profile_file(path: Path) -> dict[str, Any] | None:
    suffix = path.suffix.lower()
    if suffix == ".h5ad":
        return _profile_h5ad(path)
    elif suffix == ".h5":
        # Try as h5ad first, fallback to loom-style
        try:
            return _profile_h5ad(path)
        except Exception:
            return {"filename": path.name, "path": str(path), "format": "h5", "note": "could not parse as h5ad"}
    elif suffix == ".loom":
        return _profile_loom(path)
    elif suffix in (".csv", ".tsv", ".txt"):
        return _profile_tabular(path)
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def profile_workspace(
    data_paths: str | Path | list[str | Path],
    user_context: dict[str, Any] | str | None = None,
) -> dict[str, Any]:
    """Profile all data files and merge with user-provided biological context.

    Args:
        data_paths:   A file path, directory path, or list of file/directory paths.
                      Directories are scanned for supported file types.
                      Supported formats: h5ad, loom, csv, tsv.
        user_context: User-provided biological context.
                      Keys tissue, disease, modality, notes are merged as-is.
                      Structural keys (files, n_cells, etc.) are always from the files.

    Returns:
        A workspace profile dict with a "files" list and merged user context.
    """
    if isinstance(user_context, str):
        user_context = {"notes": user_context}
    user_context = dict(user_context or {})

    # Normalise data_paths to a flat list of Path objects
    if isinstance(data_paths, (str, Path)):
        raw = [Path(data_paths)]
    else:
        raw = [Path(p) for p in data_paths]

    # Expand directories
    candidates: list[Path] = []
    for p in raw:
        if p.is_dir():
            for ext in _SUPPORTED_EXTENSIONS:
                candidates.extend(sorted(p.glob(f"*{ext}")))
        else:
            candidates.append(p)

    # Profile each file
    file_profiles: list[dict[str, Any]] = []
    for path in candidates:
        result = _profile_file(path)
        if result is not None:
            file_profiles.append(result)

    profile: dict[str, Any] = {"files": file_profiles}

    # Merge user context — structural keys never come from user
    _STRUCTURAL_KEYS = {"files"}
    for key, val in user_context.items():
        if key not in _STRUCTURAL_KEYS:
            profile[key] = val

    return profile
