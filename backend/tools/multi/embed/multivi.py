"""Multi-omic joint embedding via MultiVI (scvi-tools).

MultiVI is a deep generative model for paired RNA+ATAC data. It learns a
joint latent space that handles both count distributions and can optionally
correct batch effects within the model.

Reference: Ashuach et al. 2023 (Nature Methods)
"""

from __future__ import annotations

from pathlib import Path


def run(
    adata,
    *,
    atac_h5ad_path: str | Path | None = None,
    batch_key: str | None = None,
    n_latent: int = 20,
    n_epochs: int = 500,
    use_gpu: bool = True,
    output_dir: Path | None = None,
) -> object:
    """Train MultiVI and compute joint RNA+ATAC embedding.

    Args:
        adata: RNA AnnData with raw counts in adata.X or adata.layers["counts"].
               Must share barcodes with the ATAC adata (run multi_qc_intersect first).
        atac_h5ad_path: Path to paired ATAC AnnData. If None, reads from
                        adata.uns["atac_h5ad_path"].
        batch_key: adata.obs column for batch correction within MultiVI.
                   If None, no batch correction applied.
        n_latent: Dimensionality of the joint latent space (default 20).
        n_epochs: Training epochs (default 500; use 200 for quick exploration).
        use_gpu: Use GPU/MPS if available (default True).
        output_dir: If provided, saves the trained model here for later use.

    Returns:
        adata with:
        - adata.obsm["X_multivi"]: joint latent representation (cells × n_latent)
        - adata.uns["multivi_model_path"]: path to saved model (if output_dir given)
    """
    import anndata as ad
    import scvi
    import muon as mu

    atac_path = _resolve_atac_path(adata, atac_h5ad_path)
    atac = ad.read_h5ad(atac_path)

    _validate_paired(adata, atac)

    # Ensure raw counts are accessible BEFORE building MuData so the
    # layers are present in mdata["rna"] and mdata["atac"] from the start.
    if "counts" not in adata.layers:
        adata.layers["counts"] = adata.X.copy()
    if "counts" not in atac.layers:
        atac.layers["counts"] = atac.X.copy()

    # Build MuData for MultiVI setup
    mdata = mu.MuData({"rna": adata, "atac": atac})

    # scvi-tools ≥ 1.0 requires an explicit `modalities` dict mapping each
    # data key → the MuData modality it lives in.  Without it the call raises
    # "Modalities cannot be None."
    modalities: dict = {
        "rna_layer": "rna",
        "atac_layer": "atac",
    }
    if batch_key is not None:
        modalities["batch_key"] = "rna"

    # Setup MultiVI
    scvi.model.MULTIVI.setup_mudata(
        mdata,
        rna_layer="counts",
        atac_layer="counts",
        batch_key=batch_key,
        modalities=modalities,
    )

    model = scvi.model.MULTIVI(
        mdata,
        n_latent=n_latent,
    )

    accelerator = _get_accelerator(use_gpu)
    model.train(
        max_epochs=n_epochs,
        early_stopping=True,
        accelerator=accelerator,
    )

    # Extract joint latent representation
    latent = model.get_latent_representation()
    adata.obsm["X_multivi"] = latent

    if output_dir is not None:
        output_dir = Path(output_dir)
        model_path = output_dir / "multivi_model"
        model.save(str(model_path), overwrite=True)
        adata.uns["multivi_model_path"] = str(model_path)

    adata.uns["multivi"] = {
        "n_latent": n_latent,
        "n_epochs": n_epochs,
        "batch_key": batch_key,
        "embedding_key": "X_multivi",
    }

    return adata


def _get_accelerator(use_gpu: bool) -> str:
    """Return the best available accelerator string for scvi-tools trainer."""
    if not use_gpu:
        return "cpu"
    import torch
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _resolve_atac_path(adata, explicit_path) -> Path:
    if explicit_path is not None:
        p = Path(explicit_path)
        if not p.exists():
            raise FileNotFoundError(f"ATAC AnnData not found: {p}")
        return p
    stored = adata.uns.get("atac_h5ad_path")
    if stored is None:
        raise ValueError(
            "atac_h5ad_path must be provided or stored in adata.uns['atac_h5ad_path']. "
            "Run multi_qc_intersect first to align barcodes and set this path."
        )
    p = Path(stored)
    if not p.exists():
        raise FileNotFoundError(f"atac_h5ad_path in adata.uns not found: {p}")
    return p


def _validate_paired(rna, atac) -> None:
    if rna.n_obs != atac.n_obs:
        raise ValueError(
            f"RNA ({rna.n_obs} cells) and ATAC ({atac.n_obs} cells) must have the same cells. "
            "Run multi_qc_intersect to align barcodes."
        )
    if not all(rna.obs_names == atac.obs_names):
        raise ValueError(
            "Cell barcodes do not match between RNA and ATAC. "
            "Run multi_qc_intersect to align barcodes."
        )
