"""RNA velocity using scVelo (dynamical/stochastic/deterministic mode).

Fits per-gene unspliced/spliced kinetics from velocyto-derived Mu/Ms layers.
Use as an RNA-only velocity baseline, or when ATAC data is unavailable.

Prerequisites:
  - adata.layers["Mu"] and adata.layers["Ms"] from velocyto
  - adata.obsm[embedding_key] (default "X_pca", auto-wired from rna_embed_pca)
  - Optional: adata.var["highly_variable"] from rna_feature_selection_scanpy_hvg

scVelo ≥ 0.4.0: neighbors must be pre-computed before moments() to avoid
DeprecationWarnings. This tool calls sc.pp.neighbors() explicitly.
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path

from backend.types import VelocityResult

logger = logging.getLogger(__name__)


def run(
    adata,
    *,
    embedding_key: str = "X_pca",
    min_shared_counts: int = 20,
    n_pcs: int = 30,
    n_neighbors: int = 30,
    mode: str = "dynamical",
    compute_latent_time: bool = True,
    output_dir: Path | None = None,
) -> VelocityResult:
    """Compute RNA velocity with scVelo.

    Args:
        adata: AnnData with velocyto layers (adata.layers["spliced"],
               adata.layers["unspliced"]). Smoothed moments (Mu/Ms) are
               computed internally by scv.pp.moments().
        embedding_key: Embedding to use for neighbor graph construction
                       (auto-wired from adata.uns["embedding"]["obsm_key"],
                       default "X_pca"). Must exist in adata.obsm.
        min_shared_counts: Minimum shared spliced/unspliced counts per gene
                           for velocity gene selection (default 20).
        n_pcs: Number of PCs used internally by scVelo moments (default 30).
        n_neighbors: Number of neighbors for the velocity graph (default 30).
        mode: Velocity mode — "dynamical" (default, fits full kinetics),
              "stochastic", or "deterministic".
        compute_latent_time: Infer global pseudotime from velocity (default True).
                             Requires mode="dynamical".
        output_dir: If provided, saves gene-level parameters to
                    scvelo_gene_params.parquet.

    Returns:
        VelocityResult with n_velocity_genes, mean_likelihood, and metadata.
        Velocity stored in adata.layers["velocity"];
        latent time in adata.obs["latent_time"] if compute_latent_time=True.
    """
    for layer in ("spliced", "unspliced"):
        if layer not in adata.layers:
            raise ValueError(
                f"adata.layers['{layer}'] not found. "
                "Run velocyto on your BAM files to generate spliced/unspliced counts."
            )

    _VALID_MODES = {"dynamical", "stochastic", "deterministic"}
    if mode not in _VALID_MODES:
        raise ValueError(
            f"mode='{mode}' is not valid. Choose from {sorted(_VALID_MODES)}."
        )

    if embedding_key not in adata.obsm:
        raise ValueError(
            f"Embedding '{embedding_key}' not found in adata.obsm. "
            f"Run rna_embed_pca first. Available: {list(adata.obsm.keys())}"
        )

    if "highly_variable" not in adata.var:
        warnings.warn(
            "adata.var['highly_variable'] not found. Run rna_feature_selection_scanpy_hvg "
            "first for best results. Continuing with all genes.",
            UserWarning,
            stacklevel=2,
        )

    return _run_scvelo(
        adata,
        embedding_key=embedding_key,
        min_shared_counts=min_shared_counts,
        n_pcs=n_pcs,
        n_neighbors=n_neighbors,
        mode=mode,
        compute_latent_time=compute_latent_time,
        output_dir=Path(output_dir) if output_dir else None,
    )


def _run_scvelo(
    adata,
    *,
    embedding_key,
    min_shared_counts,
    n_pcs,
    n_neighbors,
    mode,
    compute_latent_time,
    output_dir,
) -> VelocityResult:
    import numpy as np
    import scanpy as sc
    import scvelo as scv

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: velocity-specific gene filtering + normalization
    scv.pp.filter_and_normalize(adata, min_shared_counts=min_shared_counts)

    # Step 2: pre-compute neighbors explicitly (avoids scVelo ≥0.4.0 DeprecationWarning)
    sc.pp.neighbors(adata, n_neighbors=n_neighbors, n_pcs=n_pcs, use_rep=embedding_key)
    scv.pp.moments(adata)  # uses the pre-computed neighbor graph

    # Step 3: dynamics recovery (dynamical mode only)
    if mode == "dynamical":
        logger.info("Recovering dynamics (dynamical mode) — this may take several minutes")
        scv.tl.recover_dynamics(adata)

    # Step 4: velocity
    scv.tl.velocity(adata, mode=mode)

    # Step 5: velocity graph
    scv.tl.velocity_graph(adata, n_jobs=1, show_progress_bar=False)

    # Step 6: latent time
    latent_time_key = None
    if compute_latent_time:
        if mode != "dynamical":
            logger.warning(
                "compute_latent_time=True requires mode='dynamical'; skipping latent time."
            )
        else:
            scv.tl.latent_time(adata)
            latent_time_key = "latent_time"
            logger.info("Latent time computed → adata.obs['latent_time']")

    # Step 7: extract summary statistics
    n_velocity_genes = int(adata.var["velocity_genes"].sum()) if "velocity_genes" in adata.var else 0

    mean_likelihood = 0.0
    if "fit_likelihood" in adata.var:
        mean_likelihood = float(
            adata.var["fit_likelihood"].dropna().mean()
            if hasattr(adata.var["fit_likelihood"], "dropna")
            else np.nanmean(adata.var["fit_likelihood"].values)
        )

    # Step 8: save gene params
    params_path = None
    if output_dir is not None and "fit_alpha" in adata.var:
        import pandas as pd
        fit_cols = [c for c in adata.var.columns if c.startswith("fit_") or c == "velocity_genes"]
        params_df = adata.var[fit_cols]
        params_path = output_dir / "scvelo_gene_params.parquet"
        params_df.to_parquet(params_path)
        logger.info("Gene params saved to %s", params_path)

    # Step 9: write adata.uns
    adata.uns["scvelo"] = {
        "mode": mode,
        "min_shared_counts": min_shared_counts,
        "n_pcs": n_pcs,
        "n_neighbors": n_neighbors,
        "embedding_key": embedding_key,
        "mean_likelihood": mean_likelihood,
        "n_velocity_genes": n_velocity_genes,
    }
    adata.uns["velocity"] = {
        "method": "scvelo",
        "velocity_key": "velocity",
        "velocity_keys": ["velocity"],
        "latent_time_key": latent_time_key,
        "n_velocity_genes": n_velocity_genes,
        "fit_complete": True,
    }

    logger.info(
        "scVelo (%s) complete: %d velocity genes, mean likelihood %.3f",
        mode, n_velocity_genes, mean_likelihood,
    )

    return VelocityResult(
        method="scvelo",
        n_velocity_genes=n_velocity_genes,
        velocity_key="velocity",
        latent_time_key=latent_time_key,
        model_distribution={},
        mean_likelihood=mean_likelihood,
        params_path=params_path,
        metadata={
            "mode": mode,
            "min_shared_counts": min_shared_counts,
            "n_pcs": n_pcs,
            "n_neighbors": n_neighbors,
            "embedding_key": embedding_key,
        },
    )
