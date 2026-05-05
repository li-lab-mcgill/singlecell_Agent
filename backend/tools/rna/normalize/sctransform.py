"""SCTransform normalization via R runner (variance-stabilizing transformation)."""

from __future__ import annotations

import tempfile
from pathlib import Path


def run(adata, *, runners):
    return _run_r_normalization(adata, runners=runners, script_name="rna/normalization_sctransform.R", method="sctransform")


def _run_r_normalization(adata, *, runners, script_name: str, method: str):
    from backend.rna._normalization import (
        _write_r_count_matrix_inputs,
        _read_cells_by_genes_matrix,
    )

    if runners is None or getattr(runners, "r", None) is None:
        raise RuntimeError(f"{method} normalization requires the R runner.")

    tmp_input_matrix = tempfile.NamedTemporaryFile(suffix=".counts.mtx", delete=False)
    tmp_matrix = tempfile.NamedTemporaryFile(suffix=".mtx", delete=False)
    tmp_input_genes = tempfile.NamedTemporaryFile(suffix=".input.genes.txt", delete=False)
    tmp_input_cells = tempfile.NamedTemporaryFile(suffix=".input.cells.txt", delete=False)
    tmp_genes = tempfile.NamedTemporaryFile(suffix=".genes.txt", delete=False)
    tmp_cells = tempfile.NamedTemporaryFile(suffix=".cells.txt", delete=False)
    for f in (tmp_input_matrix, tmp_matrix, tmp_input_genes, tmp_input_cells, tmp_genes, tmp_cells):
        f.close()
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
        for p in (tmp_input_matrix.name, tmp_input_genes.name, tmp_input_cells.name,
                  tmp_matrix.name, tmp_genes.name, tmp_cells.name):
            Path(p).unlink(missing_ok=True)
