"""RNA dimensionality reduction / latent embedding: PCA, scVI, Seurat PCA, scANVI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from ..training import build_lightning_train_config

KNOWN_METHODS = ("pca", "scvi", "seurat_pca", "scanvi")


def dispatch(adata, *, method: str, refs=None, runners=None, **kwargs: Any):
    if method == "pca":
        return _run_pca(adata, **kwargs)
    if method == "scvi":
        return _run_scvi(adata, **kwargs)
    if method == "seurat_pca":
        return _run_seurat_pca(adata, runners=runners, **kwargs)
    if method == "scanvi":
        return _run_scanvi(adata, **kwargs)
    raise ValueError(f"Unknown rna.embed method: {method}. Choose from {KNOWN_METHODS}.")


def _run_pca(adata, *, n_pcs: int = 50, random_seed: int = 42, **_: Any):
    import scanpy as sc

    sc.pp.pca(adata, n_comps=n_pcs, random_state=random_seed)
    adata.uns["embedding"] = {"method": "pca", "n_pcs": n_pcs, "obsm_key": "X_pca"}
    return adata


def _run_scvi(
    adata,
    *,
    batch_key: Optional[str] = None,
    n_latent: int = 30,
    n_layers: int = 2,
    n_epochs: Optional[int] = None,
    random_seed: int = 42,
    accelerator: str = "auto",
    devices: str | int = "auto",
    precision: str | int | None = None,
    **_: Any,
):
    import scvi

    if "counts" not in adata.layers:
        adata.layers["counts"] = adata.X.copy()

    scvi.settings.seed = random_seed
    setup_kwargs = {"layer": "counts"}
    if batch_key and batch_key in adata.obs.columns:
        setup_kwargs["batch_key"] = batch_key
    scvi.model.SCVI.setup_anndata(adata, **setup_kwargs)
    model = scvi.model.SCVI(
        adata,
        gene_likelihood="nb",
        n_layers=n_layers,
        n_latent=n_latent,
    )
    train_kwargs, training = build_lightning_train_config(
        accelerator=accelerator,
        devices=devices,
        precision=precision,
    )
    if n_epochs is not None:
        train_kwargs["max_epochs"] = n_epochs
    model.train(**train_kwargs)
    adata.obsm["X_scvi"] = model.get_latent_representation()
    adata.uns["embedding"] = {
        "method": "scvi",
        "n_latent": n_latent,
        "n_layers": n_layers,
        "batch_key": batch_key,
        "obsm_key": "X_scvi",
        "training": training,
    }
    return adata


def _run_seurat_pca(adata, *, runners, n_pcs: int = 50, random_seed: int = 42, **_: Any):
    if runners is None or runners.r is None:
        raise RuntimeError("Seurat PCA requires the R runner. Pass runners=RunnerSuite(...).")
    import os
    import tempfile

    import anndata as ad

    tmp_in = tempfile.NamedTemporaryFile(suffix=".h5ad", delete=False)
    tmp_out = tempfile.NamedTemporaryFile(suffix=".h5ad", delete=False)
    tmp_in.close(); tmp_out.close()
    try:
        adata.write_h5ad(tmp_in.name)
        script_result = runners.r.run_script(
            "rna/dimreduction_seurat_pca.R",
            args={"input_h5ad": tmp_in.name, "output_h5ad": tmp_out.name, "n_pcs": n_pcs, "seed": random_seed},
            returns="json",
        )
        if not Path(tmp_out.name).exists() or Path(tmp_out.name).stat().st_size == 0:
            raise RuntimeError("Seurat PCA R script completed but did not write a non-empty output h5ad.")
        new_adata = ad.read_h5ad(tmp_out.name)
    finally:
        for tmp_path in (tmp_in.name, tmp_out.name):
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass

    _ensure_seurat_pca_embedding(new_adata, script_result=script_result)
    new_adata.uns["embedding"] = {"method": "seurat_pca", "n_pcs": n_pcs, "obsm_key": "X_seurat_pca"}
    return new_adata


def _ensure_seurat_pca_embedding(adata, *, script_result: Any = None) -> None:
    obsm = getattr(adata, "obsm", None)
    if obsm is None:
        raise RuntimeError("Seurat PCA output AnnData has no obsm container.")
    if "X_seurat_pca" in obsm:
        return

    # zellkonverter may either preserve reducedDim names directly or add the
    # AnnData-style X_ prefix. Canonicalize both forms for downstream tools.
    for alias in ("seurat_pca", "X_X_seurat_pca"):
        if alias in obsm:
            obsm["X_seurat_pca"] = obsm[alias]
            return

    available = sorted(list(obsm.keys()))
    detail = ""
    if isinstance(script_result, dict):
        detail = f" R result: {script_result}"
    raise RuntimeError(
        "Seurat PCA R script completed but output h5ad did not contain "
        f"adata.obsm['X_seurat_pca']. Available obsm keys: {available}.{detail}"
    )


def _run_scanvi(
    adata,
    *,
    batch_key: Optional[str] = None,
    label_key: Optional[str] = None,
    n_latent: int = 30,
    n_epochs: Optional[int] = None,
    accelerator: str = "auto",
    devices: str | int = "auto",
    precision: str | int | None = None,
    **_: Any,
):
    if label_key is None:
        raise ValueError("scanvi requires label_key (obs column with partial cell-type labels).")
    if label_key not in adata.obs:
        raise ValueError(f"scanvi label_key '{label_key}' not found in adata.obs.")
    import scvi

    if "counts" not in adata.layers:
        adata.layers["counts"] = adata.X.copy()

    scvi.model.SCANVI.setup_anndata(
        adata,
        batch_key=batch_key,
        labels_key=label_key,
        unlabeled_category="Unknown",
        layer="counts",
    )
    model = scvi.model.SCANVI(adata, n_latent=n_latent)
    train_kwargs, training = build_lightning_train_config(
        accelerator=accelerator,
        devices=devices,
        precision=precision,
    )
    if n_epochs is not None:
        train_kwargs["max_epochs"] = n_epochs
    model.train(**train_kwargs)
    adata.obsm["X_scanvi"] = model.get_latent_representation()
    adata.uns["embedding"] = {
        "method": "scanvi",
        "n_latent": n_latent,
        "obsm_key": "X_scanvi",
        "training": training,
    }
    return adata
