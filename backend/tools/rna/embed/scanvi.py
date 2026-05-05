"""scANVI semi-supervised embedding using partial cell type labels."""

from __future__ import annotations


def run(
    adata,
    *,
    label_key: str,
    batch_key: str | None = None,
    n_latent: int = 30,
    n_epochs: int | None = None,
    accelerator: str = "auto",
    devices: str | int = "auto",
    precision: str | int | None = None,
):
    import scvi
    from backend.rna.training import build_lightning_train_config

    if label_key not in adata.obs:
        raise ValueError(f"label_key '{label_key}' not found in adata.obs.")
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
        accelerator=accelerator, devices=devices, precision=precision
    )
    if n_epochs is not None:
        train_kwargs["max_epochs"] = n_epochs
    model.train(**train_kwargs)
    adata.obsm["X_scanvi"] = model.get_latent_representation()
    adata.uns["embedding"] = {
        "method": "scanvi",
        "n_latent": n_latent,
        "label_key": label_key,
        "batch_key": batch_key,
        "obsm_key": "X_scanvi",
        "training": training,
    }
    return adata
