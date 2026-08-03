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
    embedding_key: str = "X_scvi",
):
    import scvi
    from backend.training import build_lightning_train_config

    if "counts" not in adata.layers:
        adata.layers["counts"] = adata.X.copy()
    if batch_key and batch_key not in adata.obs:
        raise ValueError(f"batch_key '{batch_key}' not found in adata.obs.")

    scvi.settings.seed = random_seed
    setup_kwargs = {"layer": "counts"}
    if batch_key:
        setup_kwargs["batch_key"] = batch_key
    scvi.model.SCVI.setup_anndata(adata, **setup_kwargs)
    model = scvi.model.SCVI(adata, gene_likelihood="nb", n_layers=n_layers, n_latent=n_latent)
    train_kwargs, training = build_lightning_train_config(
        accelerator=accelerator, devices=devices, precision=precision
    )
    if n_epochs is not None:
        train_kwargs["max_epochs"] = n_epochs
    model.train(**train_kwargs)
    adata.obsm[embedding_key] = model.get_latent_representation()
    if adata.obsm[embedding_key].shape[0] != adata.n_obs:
        raise RuntimeError(
            f"scVI latent representation has shape {adata.obsm[embedding_key].shape}, "
            f"expected first dimension n_obs={adata.n_obs}."
        )
    adata.uns["embedding"] = {
        "method": "scvi",
        "n_latent": n_latent,
        "n_layers": n_layers,
        "batch_key": batch_key,
        "obsm_key": embedding_key,
        "training": training,
    }
    return adata
