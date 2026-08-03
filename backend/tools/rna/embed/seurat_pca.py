"""Seurat PCA dimensionality reduction via Rscript subprocess."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

_R_SCRIPT = Path(__file__).parents[3] / "r_scripts" / "rna" / "dimreduction_seurat_pca.R"


def run(
    adata,
    *,
    n_pcs: int = 50,
    random_seed: int = 42,
    embedding_key: str = "X_seurat_pca",
):
    import anndata as ad
    from backend.rna._dimensionality_reduction import _ensure_seurat_pca_embedding

    _check_rscript()

    tmp_in = tempfile.NamedTemporaryFile(suffix=".h5ad", delete=False)
    tmp_out = tempfile.NamedTemporaryFile(suffix=".h5ad", delete=False)
    tmp_in.close()
    tmp_out.close()
    try:
        adata.write_h5ad(tmp_in.name)

        args = {
            "input_h5ad": tmp_in.name,
            "output_h5ad": tmp_out.name,
            "n_pcs": n_pcs,
            "seed": random_seed,
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(args, f)
            args_path = f.name

        env = {**os.environ, "KMP_DUPLICATE_LIB_OK": "TRUE", "OMP_NUM_THREADS": "1"}
        try:
            proc = subprocess.run(
                ["Rscript", "--no-init-file", str(_R_SCRIPT), "--args-json", args_path],
                capture_output=True,
                text=True,
                env=env,
            )
        finally:
            Path(args_path).unlink(missing_ok=True)

        if proc.returncode != 0:
            raise RuntimeError(
                f"Seurat PCA R script failed (exit {proc.returncode}):\n"
                f"STDERR:\n{proc.stderr}\nSTDOUT:\n{proc.stdout}"
            )

        # Parse last valid JSON line from stdout
        script_result = {}
        for line in reversed(proc.stdout.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                script_result = json.loads(line)
                break
            except json.JSONDecodeError:
                continue

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
    if embedding_key != "X_seurat_pca" and "X_seurat_pca" in new_adata.obsm:
        new_adata.obsm[embedding_key] = new_adata.obsm["X_seurat_pca"]
    new_adata.uns["embedding"] = {"method": "seurat_pca", "n_pcs": n_pcs, "obsm_key": embedding_key}
    return new_adata


def _check_rscript() -> None:
    result = subprocess.run(["Rscript", "--version"], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("Rscript not found on PATH. Install R from https://cran.r-project.org/")
    _ensure_r_packages(["jsonlite"], bioc=False)
    _ensure_r_packages(["Seurat"], bioc=False)


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
