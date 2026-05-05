"""scVI variational autoencoder embedding. Supports optional batch correction via batch_key."""

from __future__ import annotations


def run(
    adata,
    *,
    batch_key: str | None = None,
    n_latent: int = 30,
    n_layers: int = 2,
    n_epochs: int | None = None,
    random_seed: int = 42,
    accelerator: str = "auto",
    devices: str | int = "auto",
    precision: str | int | None = None,
):
    import scvi
    from backend.rna.training import build_lightning_train_config

    if "counts" not in adata.layers:
        adata.layers["counts"] = adata.X.copy()

    scvi.settings.seed = random_seed
    setup_kwargs = {"layer": "counts"}
    if batch_key and batch_key in adata.obs.columns:
        setup_kwargs["batch_key"] = batch_key
    scvi.model.SCVI.setup_anndata(adata, **setup_kwargs)
    model = scvi.model.SCVI(adata, gene_likelihood="nb", n_layers=n_layers, n_latent=n_latent)
    train_kwargs, training = build_lightning_train_config(
        accelerator=accelerator, devices=devices, precision=precision
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
