"""RNA normalization: log1p, scran."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Optional

KNOWN_METHODS = ("log1p", "scran")


def dispatch(adata, *, method: str, runners: Optional[Any] = None, target_sum: float = 1e4, **kwargs: Any):
    if method == "log1p":
        return _run_log1p(adata, target_sum=target_sum)
    if method == "scran":
        return _run_scran(adata, runners=runners, **kwargs)
    raise ValueError(f"Unknown rna.normalize method: {method}. Choose from {KNOWN_METHODS}.")


def _run_log1p(adata, *, target_sum: float):
    import scanpy as sc

    if "counts" not in adata.layers:
        adata.layers["counts"] = adata.X.copy()
    sc.pp.normalize_total(adata, target_sum=target_sum)
    sc.pp.log1p(adata)
    adata.uns["normalization"] = {"method": "log1p", "target_sum": target_sum}
    return adata


def _run_scran(adata, *, runners, **_: Any):
    return _run_r_normalization(
        adata,
        runners=runners,
        script_name="rna/normalization_scran.R",
        method="scran",
    )


def _run_r_normalization(adata, *, runners, script_name: str, method: str):
    if runners is None or getattr(runners, "r", None) is None:
        raise RuntimeError(f"{method} normalization requires the R runner. Pass runners=RunnerSuite(...).")

    tmp_input_matrix = tempfile.NamedTemporaryFile(suffix=".counts.mtx", delete=False)
    tmp_matrix = tempfile.NamedTemporaryFile(suffix=".mtx", delete=False)
    tmp_input_genes = tempfile.NamedTemporaryFile(suffix=".input.genes.txt", delete=False)
    tmp_input_cells = tempfile.NamedTemporaryFile(suffix=".input.cells.txt", delete=False)
    tmp_genes = tempfile.NamedTemporaryFile(suffix=".genes.txt", delete=False)
    tmp_cells = tempfile.NamedTemporaryFile(suffix=".cells.txt", delete=False)
    tmp_input_matrix.close()
    tmp_matrix.close()
    tmp_input_genes.close()
    tmp_input_cells.close()
    tmp_genes.close()
    tmp_cells.close()
    try:
        _write_r_count_matrix_inputs(
            adata,
            matrix_path=Path(tmp_input_matrix.name),
            genes_path=Path(tmp_input_genes.name),
            cells_path=Path(tmp_input_cells.name),
            method=method,
        )
        runners.r.run_script(
            script_name,
            args={
                "input_matrix": tmp_input_matrix.name,
                "input_genes": tmp_input_genes.name,
                "input_cells": tmp_input_cells.name,
                "output_matrix": tmp_matrix.name,
                "output_genes": tmp_genes.name,
                "output_cells": tmp_cells.name,
            },
            returns="json",
        )
        normalized = _read_cells_by_genes_matrix(
            matrix_path=Path(tmp_matrix.name),
            genes_path=Path(tmp_genes.name),
            cells_path=Path(tmp_cells.name),
            adata=adata,
            method=method,
        )
        new_adata = adata.copy()
        new_adata.X = normalized
        new_adata.uns["normalization"] = {"method": method}
        return new_adata
    finally:
        Path(tmp_input_matrix.name).unlink(missing_ok=True)
        Path(tmp_input_genes.name).unlink(missing_ok=True)
        Path(tmp_input_cells.name).unlink(missing_ok=True)
        Path(tmp_matrix.name).unlink(missing_ok=True)
        Path(tmp_genes.name).unlink(missing_ok=True)
        Path(tmp_cells.name).unlink(missing_ok=True)


def _write_r_count_matrix_inputs(
    adata,
    *,
    matrix_path: Path,
    genes_path: Path,
    cells_path: Path,
    method: str,
) -> None:
    from scipy.io import mmwrite

    matrix, _source = _select_count_matrix(adata, method=method)
    mmwrite(matrix_path, matrix.T.tocsr())
    genes_path.write_text("\n".join(str(x) for x in adata.var_names) + "\n", encoding="utf-8")
    cells_path.write_text("\n".join(str(x) for x in adata.obs_names) + "\n", encoding="utf-8")


def _select_count_matrix(adata, *, method: str):
    from scipy import sparse

    layers = getattr(adata, "layers", {})
    if "counts" in layers:
        matrix = layers["counts"]
        source = "layers['counts']"
    else:
        matrix = getattr(adata, "X", None)
        source = "X"
        if matrix is None:
            raise ValueError(
                f"{method} requires raw counts in adata.layers['counts'] or integer-like non-negative adata.X."
            )

    if not _is_count_like_matrix(matrix):
        raise ValueError(
            f"{method} requires integer-like non-negative raw counts; {source} does not look like counts."
        )

    if not sparse.issparse(matrix):
        matrix = sparse.csr_matrix(matrix)
    return matrix, source


def _is_count_like_matrix(matrix) -> bool:
    import numpy as np
    from scipy import sparse

    values = matrix.data if sparse.issparse(matrix) else np.asarray(matrix).ravel()
    if values.size == 0:
        return True
    if not np.all(np.isfinite(values)):
        return False
    if np.any(values < 0):
        return False
    return bool(np.allclose(values, np.rint(values), atol=1e-6))


def _read_cells_by_genes_matrix(*, matrix_path: Path, genes_path: Path, cells_path: Path, adata, method: str):
    from scipy.io import mmread

    if not matrix_path.is_file() or matrix_path.stat().st_size == 0:
        raise RuntimeError(f"{method} normalization did not write a non-empty matrix: {matrix_path}")

    matrix = mmread(matrix_path).tocsr()
    genes = _read_names(genes_path)
    cells = _read_names(cells_path)
    expected_genes = [str(x) for x in adata.var_names]
    expected_cells = [str(x) for x in adata.obs_names]

    if matrix.shape != (len(cells), len(genes)):
        raise RuntimeError(
            f"{method} normalization matrix shape {matrix.shape} does not match "
            f"cells x genes ({len(cells)}, {len(genes)})."
        )

    matrix = _reorder_axis(matrix, cells, expected_cells, axis=0, label="cells", method=method)
    matrix = _reorder_axis(matrix, genes, expected_genes, axis=1, label="genes", method=method)
    return matrix


def _read_names(path: Path) -> list[str]:
    if not path.is_file():
        raise RuntimeError(f"Expected names file was not written: {path}")
    return [line.rstrip("\n") for line in path.read_text(encoding="utf-8").splitlines()]


def _reorder_axis(matrix, source_names: list[str], target_names: list[str], *, axis: int, label: str, method: str):
    if source_names == target_names:
        return matrix
    if set(source_names) != set(target_names):
        missing = sorted(set(target_names) - set(source_names))[:10]
        extra = sorted(set(source_names) - set(target_names))[:10]
        raise RuntimeError(
            f"{method} normalization returned different {label}. Missing: {missing}; extra: {extra}."
        )
    positions = {name: i for i, name in enumerate(source_names)}
    order = [positions[name] for name in target_names]
    if axis == 0:
        return matrix[order, :]
    return matrix[:, order]
