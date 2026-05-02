"""RNA batch integration: Harmony, LIGER, scVI, BBKNN, Scanorama."""

from __future__ import annotations

from typing import Any, Optional

from ..training import build_lightning_train_config

KNOWN_METHODS = ("harmony", "liger", "scvi", "bbknn", "scanorama")

def dispatch(adata, *, method: str, batch_key: str, embedding_key: str = "X_pca",
             refs=None, runners=None, **kwargs: Any):
    if not batch_key:
        raise ValueError("batch_key is required for batch integration.")
    if batch_key not in adata.obs:
        raise ValueError(f"batch_key '{batch_key}' not found in adata.obs.")

    if method == "harmony":
        return _run_harmony(adata, batch_key=batch_key, embedding_key=embedding_key, **kwargs)
    if method == "liger":
        return _run_liger(adata, batch_key=batch_key, runners=runners, **kwargs)
    if method == "scvi":
        return _run_scvi(adata, batch_key=batch_key, **kwargs)
    if method == "bbknn":
        return _run_bbknn(adata, batch_key=batch_key, embedding_key=embedding_key, **kwargs)
    if method == "scanorama":
        if embedding_key != "X_pca":
            raise ValueError(
                "scanorama integrates expression matrices, not a precomputed embedding. "
                "Omit embedding_key or use the default 'X_pca'; output is always adata.obsm['X_scanorama']."
            )
        return _run_scanorama(adata, batch_key=batch_key, **kwargs)
    raise ValueError(f"Unknown rna.integrate method: {method}. Choose from {KNOWN_METHODS}.")


def _run_harmony(
    adata,
    *,
    batch_key: str,
    embedding_key: str = "X_pca",
    n_pcs: int = 50,
    theta: float = 2.0,
    **_: Any,
):
    import scanpy as sc
    from harmonypy import run_harmony

    if embedding_key not in adata.obsm:
        if embedding_key == "X_pca":
            sc.pp.pca(adata, n_comps=n_pcs)
        else:
            raise ValueError(f"embedding_key '{embedding_key}' not found in adata.obsm")
    output_key = "X_harmony" if embedding_key == "X_pca" else f"{embedding_key}_harmony"
    ho = run_harmony(adata.obsm[embedding_key], adata.obs, batch_key, theta=theta)
    adata.obsm[output_key] = ho.Z_corr.T
    adata.uns["batch_integration"] = {
        "method": "harmony",
        "batch_key": batch_key,
        "input_embedding_key": embedding_key,
        "obsm_key": output_key,
    }
    return adata


def _run_scvi(
    adata,
    *,
    batch_key: str,
    n_latent: int = 30,
    n_layers: int = 2,
    n_epochs: Optional[int] = None,
    accelerator: str = "auto",
    devices: str | int = "auto",
    precision: str | int | None = None,
    **_: Any,
):
    import scvi

    if "counts" not in adata.layers:
        adata.layers["counts"] = adata.X.copy()
    scvi.model.SCVI.setup_anndata(adata, batch_key=batch_key, layer="counts")
    model = scvi.model.SCVI(adata, n_layers=n_layers, n_latent=n_latent)
    train_kwargs, training = build_lightning_train_config(
        accelerator=accelerator,
        devices=devices,
        precision=precision,
    )
    if n_epochs is not None:
        train_kwargs["max_epochs"] = n_epochs
    model.train(**train_kwargs)
    adata.obsm["X_scvi_integrated"] = model.get_latent_representation()
    adata.uns["batch_integration"] = {
        "method": "scvi",
        "batch_key": batch_key,
        "obsm_key": "X_scvi_integrated",
        "training": training,
    }
    return adata


def _run_bbknn(
    adata,
    *,
    batch_key: str,
    embedding_key: str = "X_pca",
    neighbors_within_batch: int = 3,
    n_pcs: int = 50,
    **_: Any,
):
    import scanpy as sc
    import bbknn

    if embedding_key not in adata.obsm:
        if embedding_key == "X_pca":
            sc.pp.pca(adata, n_comps=n_pcs)
        else:
            raise ValueError(f"embedding_key '{embedding_key}' not found in adata.obsm")
    bbknn.bbknn(
        adata,
        batch_key=batch_key,
        neighbors_within_batch=neighbors_within_batch,
        n_pcs=n_pcs,
        use_rep=embedding_key,
    )
    adata.uns["batch_integration"] = {
        "method": "bbknn",
        "batch_key": batch_key,
        "input_embedding_key": embedding_key,
        "obsm_key": None,
        "modifies": "neighbors",
    }
    return adata


def _run_scanorama(adata, *, batch_key: str, dimred: int = 50, **_: Any):
    import numpy as np
    import scanorama

    batches = adata.obs[batch_key].unique().tolist()
    splits = [adata[adata.obs[batch_key] == b].copy() for b in batches]
    scanorama.integrate_scanpy(splits, dimred=dimred, return_dimred=True)
    out = np.vstack([s.obsm["X_scanorama"] for s in splits])
    # Reorder to original obs order.
    order = []
    for b in batches:
        order.extend(adata.obs.index[adata.obs[batch_key] == b].tolist())
    pos = {name: i for i, name in enumerate(order)}
    reorder = [pos[name] for name in adata.obs.index]
    adata.obsm["X_scanorama"] = out[reorder]
    adata.uns["batch_integration"] = {
        "method": "scanorama",
        "batch_key": batch_key,
        "input": "expression",
        "obsm_key": "X_scanorama",
    }
    return adata


def _run_liger(adata, *, batch_key, runners, **_: Any):
    raise NotImplementedError("TODO: LIGER via R runner (r_scripts/rna/batch_integration_liger.R)")
