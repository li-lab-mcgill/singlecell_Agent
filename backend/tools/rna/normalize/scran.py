"""Scran pooling-based normalization via Rscript subprocess."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

_R_SCRIPT = Path(__file__).parents[3] / "r_scripts" / "rna" / "normalization_scran.R"


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

        import scipy.sparse as sp

        X = adata.layers.get("counts", adata.X)
        if not sp.issparse(X):
            X = sp.csc_matrix(X.T)
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
            ["Rscript", "--no-init-file", str(_R_SCRIPT), "--args-json", str(args_json)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"scran normalization failed:\n{result.stderr}")

        # Read normalized matrix back
        import scipy.io
        mat = scipy.io.mmread(str(out_matrix_path)).toarray()
        # R writes genes × cells; transpose to cells × genes if needed
        if mat.shape[0] != adata.n_obs and mat.shape[1] == adata.n_obs:
            mat = mat.T
        if mat.shape[0] != adata.n_obs:
            raise RuntimeError(f"scran output shape {mat.shape} does not match n_obs={adata.n_obs}")
        normalized = mat
        adata = adata.copy()
        adata.X = normalized
        adata.uns["normalization"] = {"method": "scran"}

        return adata


def _check_rscript() -> None:
    result = subprocess.run(["Rscript", "--version"], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("Rscript not found on PATH. Install R from https://cran.r-project.org/")
    _ensure_r_packages(["BiocManager"], bioc=False)
    _ensure_r_packages(["scran", "scuttle"], bioc=True)


def _ensure_r_packages(packages: list[str], *, bioc: bool) -> None:
    missing_r = "c(" + ", ".join(f'"{p}"' for p in packages) + ")"
    check = f'missing <- {missing_r}[!sapply({missing_r}, requireNamespace, quietly=TRUE)]; cat(paste(missing, collapse=","))'
    res = subprocess.run(["Rscript", "--no-init-file", "-e", check], capture_output=True, text=True, timeout=30)
    missing = [p.strip() for p in res.stdout.strip().split(",") if p.strip()]
    if not missing:
        return
    missing_r2 = "c(" + ", ".join(f'"{p}"' for p in missing) + ")"
    if bioc:
        install_cmd = f'BiocManager::install({missing_r2}, ask=FALSE, update=FALSE)'
    else:
        install_cmd = f'install.packages({missing_r2}, repos="https://cloud.r-project.org")'
    res2 = subprocess.run(["Rscript", "--no-init-file", "-e", install_cmd], capture_output=True, text=True, timeout=600)
    if res2.returncode != 0:
        raise RuntimeError(f"Failed to install R packages {missing}:\n{res2.stderr}")
