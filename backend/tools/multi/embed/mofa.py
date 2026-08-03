"""Multi-omic factor decomposition via MOFA+ (Multi-Omics Factor Analysis).

MOFA+ learns shared and modality-specific latent factors that explain
variation across multiple omics layers. Unlike MultiVI/WNN (which produce
cell embeddings for clustering), MOFA+ is used when factor interpretability
and modality contribution analysis are the goal.

Reference: Argelaguet et al. 2020 (Genome Biology)
"""

from __future__ import annotations

from pathlib import Path


def run(
    adata,
    *,
    atac_h5ad_path: str | Path | None = None,
    n_factors: int = 20,
    n_epochs: int = 1000,
    convergence_mode: str = "fast",
    use_gpu: bool = False,
    output_dir: Path | None = None,
    embedding_key: str = "X_mofa",
) -> object:
    """Run MOFA+ on paired RNA+ATAC data.

    Decomposes multi-omic variation into latent factors. Each factor captures
    a source of variation that may be shared across modalities (e.g. cell cycle,
    differentiation state) or modality-specific.

    Args:
        adata: RNA AnnData with highly variable genes selected.
               Must share barcodes with ATAC adata.
        atac_h5ad_path: Path to paired ATAC AnnData with selected features.
                        If None, reads from adata.uns["atac_h5ad_path"].
        n_factors: Number of latent factors to learn (default 20).
        n_epochs: Maximum training iterations (default 1000).
        convergence_mode: "fast" (default), "medium", or "slow" — controls
                          ELBO convergence tolerance.
        use_gpu: Use GPU for training if available (default False).
        output_dir: If provided, saves MOFA model (.hdf5) here.

    Returns:
        adata with:
        - adata.obsm["X_mofa"]: factor scores (cells × n_factors)
        - adata.varm["mofa_loadings_rna"]: gene loadings per factor
        - adata.uns["mofa"]: factor metadata including variance explained
    """
    import anndata as ad
    import numpy as np
    from mudata import MuData
    import mofapy2
    from mofapy2.run.entry_point import entry_point

    atac_path = _resolve_atac_path(adata, atac_h5ad_path)
    atac = ad.read_h5ad(atac_path)

    _validate_paired(adata, atac)

    # Prepare data matrices — MOFA expects dense float matrices
    import scipy.sparse as sp

    def to_dense(X):
        if sp.issparse(X):
            return X.toarray().astype(float)
        return np.array(X, dtype=float)

    rna_matrix = to_dense(adata.X)   # cells × genes
    atac_matrix = to_dense(atac.X)   # cells × peaks

    # Subset to HVG/selected features if available
    if "highly_variable" in adata.var.columns:
        rna_matrix = rna_matrix[:, adata.var["highly_variable"].values]
        rna_var_names = adata.var_names[adata.var["highly_variable"]].tolist()
    else:
        rna_var_names = adata.var_names.tolist()

    if "selected" in atac.var.columns:
        atac_matrix = atac_matrix[:, atac.var["selected"].values]
        atac_var_names = atac.var_names[atac.var["selected"]].tolist()
    else:
        atac_var_names = atac.var_names.tolist()

    # Run MOFA+
    ent = entry_point()
    ent.set_data_options(scale_groups=False, scale_views=False)
    # mofapy2 API: data[views][groups] — outer list = views (M), inner list = groups (G)
    ent.set_data_matrix(
        [[rna_matrix], [atac_matrix]],
        likelihoods=["gaussian", "bernoulli"],
        views_names=["rna", "atac"],
        groups_names=["group1"],
    )
    ent.set_model_options(factors=n_factors, spikeslab_weights=True, ard_factors=True, ard_weights=True)
    ent.set_train_options(
        iter=n_epochs,
        convergence_mode=convergence_mode,
        gpu_mode=use_gpu,
        verbose=False,
        seed=42,
    )

    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        model_path = output_dir / "mofa_model.hdf5"
        ent.set_outfile(str(model_path))
    else:
        model_path = None

    ent.build()
    ent.run()

    # Extract factor scores and loadings
    factors = ent.model.nodes["Z"].getExpectations()["E"]  # cells × factors
    # factors shape: groups × cells × factors — take first group
    if factors.ndim == 3:
        factors = factors[0]

    w_rna = ent.model.nodes["W"].getExpectations()["E"][0]   # genes × factors (view 0 = rna)
    w_atac = ent.model.nodes["W"].getExpectations()["E"][1]  # peaks × factors (view 1 = atac)

    # Variance explained
    r2 = ent.model.calculate_variance_explained()

    if factors.shape[0] != adata.n_obs:
        factors = factors.T
    if factors.shape[0] != adata.n_obs:
        raise RuntimeError(f"MOFA+ factor shape {factors.shape} does not match n_obs={adata.n_obs}")
    adata.obsm[embedding_key] = factors
    adata.varm["mofa_loadings_rna"] = _align_loadings(w_rna, adata, rna_var_names)
    adata.uns["mofa"] = {
        "n_factors": int(n_factors),
        "n_epochs": int(n_epochs),
        "embedding_key": embedding_key,
        "model_path": str(model_path) if model_path else None,
        "variance_explained": r2 if isinstance(r2, dict) else {},
    }
    adata.uns["embedding"] = {
        "method": "mofa",
        "n_factors": int(n_factors),
        "obsm_key": embedding_key,
    }
    adata.uns["atac_h5ad_path"] = str(atac_path)

    return adata


def _align_loadings(loadings, adata, var_names) -> "np.ndarray":
    """Align factor loadings to all genes in adata.var, filling 0 for unselected."""
    import numpy as np
    n_genes = adata.n_vars
    n_factors = loadings.shape[1]
    aligned = np.zeros((n_genes, n_factors))
    var_idx = {name: i for i, name in enumerate(adata.var_names)}
    for i, name in enumerate(var_names):
        if name in var_idx:
            aligned[var_idx[name]] = loadings[i]
    return aligned


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
            "Run multi_qc_intersect first."
        )
    p = Path(stored)
    if not p.exists():
        raise FileNotFoundError(f"atac_h5ad_path in adata.uns not found: {p}")
    return p


def _validate_paired(rna, atac) -> None:
    if rna.n_obs != atac.n_obs or not all(rna.obs_names == atac.obs_names):
        raise ValueError(
            "RNA and ATAC barcodes don't match. Run multi_qc_intersect first."
        )
