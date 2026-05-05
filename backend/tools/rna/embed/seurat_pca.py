"""Seurat PCA dimensionality reduction via R runner."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def run(
    adata,
    *,
    runners,
    n_pcs: int = 50,
    random_seed: int = 42,
):
    import anndata as ad
    from backend.rna._dimensionality_reduction import _ensure_seurat_pca_embedding

    if runners is None or runners.r is None:
        raise RuntimeError("Seurat PCA requires the R runner.")

    tmp_in = tempfile.NamedTemporaryFile(suffix=".h5ad", delete=False)
    tmp_out = tempfile.NamedTemporaryFile(suffix=".h5ad", delete=False)
    tmp_in.close()
    tmp_out.close()
    try:
        adata.write_h5ad(tmp_in.name)
        script_result = runners.r.run_script(
            "rna/dimreduction_seurat_pca.R",
            args={"input_h5ad": tmp_in.name, "output_h5ad": tmp_out.name, "n_pcs": n_pcs, "seed": random_seed},
            returns="json",
        )
        if not Path(tmp_out.name).exists() or Path(tmp_out.name).stat().st_size == 0:
            raise RuntimeError("Seurat PCA R script did not write a non-empty output h5ad.")
        new_adata = ad.read_h5ad(tmp_out.name)
    finally:
        for p in (tmp_in.name, tmp_out.name):
            try:
                os.unlink(p)
            except FileNotFoundError:
                pass

    _ensure_seurat_pca_embedding(new_adata, script_result=script_result)
    new_adata.uns["embedding"] = {"method": "seurat_pca", "n_pcs": n_pcs, "obsm_key": "X_seurat_pca"}
    return new_adata
