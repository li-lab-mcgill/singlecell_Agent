"""Scran pooling-based normalization via Rscript subprocess."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import scipy.sparse as sp
import numpy as np

_R_SCRIPT = Path(__file__).parents[4] / "r_scripts" / "rna" / "normalization_scran.R"


def run(adata) -> object:
    """Normalize using scran's pooling-based size factor estimation.

    Computes cell-specific size factors using the pooling-and-deconvolution
    method (Lun et al. 2016). More accurate than library-size normalization
    for datasets with systematic count differences between cell types.
    Requires R + scran Bioconductor package.

    Args:
        adata: AnnData with raw integer counts in adata.X or adata.layers["counts"].

    Returns:
        adata with normalized log1p counts in adata.X and size factors in
        adata.obs["size_factor"].
    """
    _check_rscript()

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        # Write count matrix as MTX
        matrix_path = tmp / "counts.mtx"
        genes_path = tmp / "genes.txt"
        cells_path = tmp / "cells.txt"
        out_matrix_path = tmp / "normalized.mtx"
        out_genes_path = tmp / "out_genes.txt"
        out_cells_path = tmp / "out_cells.txt"

        X = adata.layers.get("counts", adata.X)
        if not sp.issparse(X):
            X = sp.csc_matrix(X)
        else:
            X = X.T.tocsc()  # genes × cells for MTX convention

        import scipy.io
        scipy.io.mmwrite(str(matrix_path), X)
        genes_path.write_text("\n".join(adata.var_names))
        cells_path.write_text("\n".join(adata.obs_names))

        args = {
            "input_matrix": str(matrix_path),
            "input_genes": str(genes_path),
            "input_cells": str(cells_path),
            "output_matrix": str(out_matrix_path),
            "output_genes": str(out_genes_path),
            "output_cells": str(out_cells_path),
        }
        args_json = tmp / "args.json"
        args_json.write_text(json.dumps(args))

        result = subprocess.run(
            ["Rscript", str(_R_SCRIPT), "--args-json", str(args_json)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"scran normalization failed:\n{result.stderr}")

        # Read normalized matrix back
        import scipy.io
        normalized = scipy.io.mmread(str(out_matrix_path)).T.toarray()  # back to cells × genes
        adata = adata.copy()
        adata.X = normalized
        adata.uns["normalization"] = {"method": "scran"}

        return adata


def _check_rscript() -> None:
    result = subprocess.run(["Rscript", "--version"], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "Rscript not found on PATH. Install R from https://cran.r-project.org/\n"
            "Then install scran: BiocManager::install('scran')"
        )
