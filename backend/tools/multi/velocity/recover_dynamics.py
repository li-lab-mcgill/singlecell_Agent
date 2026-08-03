"""MultiVelo core fitting: 3-ODE chromatin + RNA velocity model.

Runs mv.recover_dynamics_chrom() on paired RNA (adata) and gene-level ATAC
(adata_atac with KNN-smoothed Mc layer). Fits per-gene kinetics for chromatin
opening, transcription, splicing, and degradation rates. Classifies genes into
Model 1 (coupled) or Model 2 (decoupled chromatin + transcription).

After fitting, mv.set_velocity_genes() selects high-quality velocity genes
based on fit likelihood.

Computational note: 30–90 min for a typical dataset (5k cells × 2k genes)
with parallel=True. The executor's caching layer avoids re-running when
input SHA + params are unchanged.
"""

from __future__ import annotations

import logging
from pathlib import Path

from backend.types import VelocityResult

logger = logging.getLogger(__name__)


def run(
    adata,
    *,
    atac_h5ad_path: str | Path | None = None,
    max_iter: int = 5,
    init_mode: str = "invert",
    model_to_run: int | None = None,
    fit_decoupling: bool = True,
    neural_net: bool = False,
    adam: bool = False,
    n_anchors: int = 500,
    weight_c: float = 0.6,
    n_pcs: int = 30,
    n_neighbors: int = 30,
    likelihood_lower: float = 0.05,
    parallel: bool = True,
    n_jobs: int | None = None,
    output_dir: Path | None = None,
) -> VelocityResult:
    """Fit MultiVelo 3-ODE dynamical model to paired RNA + ATAC data.

    Args:
        adata: RNA AnnData. Must have layers["Mu"], layers["Ms"] (from velocyto)
               and obsp["connectivities"] (from multi_embed_wnn).
        atac_h5ad_path: Path to gene-level ATAC AnnData with KNN-smoothed
                        layers["Mc"] (from multi_velocity_knn_smooth). Falls
                        back to adata.uns["atac_h5ad_path"].
        max_iter: Maximum EM iterations per gene (default 5).
        init_mode: Parameter initialization strategy — "invert" (default),
                   "grid", or "simple".
        model_to_run: Force a specific model — 1 (coupled) or 2 (decoupled).
                      None (default) = auto-detect per gene.
        fit_decoupling: Enable Model 1 vs Model 2 discrimination (default True).
                        Set False to treat all genes as Model 1 (faster).
        neural_net: Use neural network–based fitting (default False).
        adam: Use Adam optimizer instead of L-BFGS-B (default False).
        n_anchors: Number of representative cells used to assign gene time
                   (default 500).
        weight_c: Weight for chromatin component in 3D distance metric for
                  anchor selection (default 0.6; RNA = 1 - weight_c).
        n_pcs: PCs used in MultiVelo's internal neighbor computation for
               anchor selection (default 30).
        n_neighbors: Neighbors used for anchor time assignment (default 30).
        likelihood_lower: Minimum per-gene fit likelihood for velocity gene
                          selection after fitting (default 0.05).
        parallel: Run gene fitting in parallel (default True).
        n_jobs: Number of parallel workers. None = os.cpu_count() in MultiVelo
                (not joblib convention). Pass an explicit int to limit CPU use.
        output_dir: If provided, saves gene parameter table to
                    multivelo_gene_params.parquet.

    Returns:
        VelocityResult. Velocity layers written to adata:
          - layers["velo_s"]: spliced velocity
          - layers["velo_u"]: unspliced velocity
          - layers["velo_chrom"]: chromatin velocity
          - layers["fit_t"]: per-cell gene time
          - layers["fit_state"]: per-cell kinetic state (0–3)
        Gene-level fit statistics in adata.var (fit_alpha, fit_beta, fit_gamma,
        fit_model, fit_likelihood, fit_likelihood_c, etc.).
    """
    for layer in ("Mu", "Ms"):
        if layer not in adata.layers:
            raise ValueError(
                f"adata.layers['{layer}'] not found. "
                "Run velocyto on your BAM files to generate spliced/unspliced counts."
            )
    if "connectivities" not in adata.obsp:
        raise ValueError(
            "adata.obsp['connectivities'] not found. "
            "Run multi_embed_wnn first to build a multi-omic neighbor graph."
        )

    atac_path = _resolve_atac_path(adata, atac_h5ad_path)
    return _run_recover_dynamics(
        adata,
        atac_path=atac_path,
        max_iter=max_iter,
        init_mode=init_mode,
        model_to_run=model_to_run,
        fit_decoupling=fit_decoupling,
        neural_net=neural_net,
        adam=adam,
        n_anchors=n_anchors,
        weight_c=weight_c,
        n_pcs=n_pcs,
        n_neighbors=n_neighbors,
        likelihood_lower=likelihood_lower,
        parallel=parallel,
        n_jobs=n_jobs,
        output_dir=Path(output_dir) if output_dir else None,
    )


from backend.tools.multi.velocity._utils import resolve_atac_path as _resolve_atac_path


def _run_recover_dynamics(
    adata,
    *,
    atac_path,
    max_iter,
    init_mode,
    model_to_run,
    fit_decoupling,
    neural_net,
    adam,
    n_anchors,
    weight_c,
    n_pcs,
    n_neighbors,
    likelihood_lower,
    parallel,
    n_jobs,
    output_dir,
) -> VelocityResult:
    import anndata as ad
    import multivelo as mv
    import numpy as np

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

    adata_atac = ad.read_h5ad(atac_path)

    if "Mc" not in adata_atac.layers:
        raise ValueError(
            "adata_atac.layers['Mc'] not found. "
            "Run multi_velocity_knn_smooth first."
        )

    # Validate gene overlap
    shared = list(set(adata.var_names) & set(adata_atac.var_names))
    if not shared:
        raise ValueError(
            f"No shared genes between RNA ({adata.n_vars}) and ATAC ({adata_atac.n_vars}). "
            "Ensure both AnnDatas use the same gene name convention."
        )
    logger.info(
        "Starting recover_dynamics_chrom: %d cells × %d shared genes",
        adata.n_obs, len(shared),
    )

    mv.recover_dynamics_chrom(
        adata,
        adata_atac=adata_atac,
        max_iter=max_iter,
        init_mode=init_mode,
        model_to_run=model_to_run,
        fit_decoupling=fit_decoupling,
        neural_net=neural_net,
        adam=adam,
        n_anchors=n_anchors,
        weight_c=weight_c,
        n_pcs=n_pcs,
        n_neighbors=n_neighbors,
        parallel=parallel,
        n_jobs=n_jobs,
    )

    # Select velocity genes by likelihood threshold
    mv.set_velocity_genes(adata, likelihood_lower=likelihood_lower)

    # Extract summary statistics
    n_velocity_genes = 0
    if "velo_s_genes" in adata.var:
        n_velocity_genes = int(adata.var["velo_s_genes"].sum())

    model_distribution: dict = {}
    if "fit_model" in adata.var:
        vc = adata.var["fit_model"].value_counts()
        model_distribution = {str(k): int(v) for k, v in vc.items()}

    mean_likelihood = 0.0
    if "fit_likelihood" in adata.var:
        mask = adata.var.get("velo_s_genes", None)
        vals = adata.var["fit_likelihood"]
        if mask is not None:
            vals = vals[mask]
        mean_likelihood = float(np.nanmean(vals.values))

    logger.info(
        "recover_dynamics_chrom complete: %d velocity genes, mean likelihood %.3f, "
        "model distribution %s",
        n_velocity_genes, mean_likelihood, model_distribution,
    )

    # Save gene parameter table
    params_path = None
    if output_dir is not None:
        fit_cols = [c for c in adata.var.columns if c.startswith("fit_") or c in ("velo_s_genes", "velo_chrom_genes")]
        if fit_cols:
            params_path = output_dir / "multivelo_gene_params.parquet"
            adata.var[fit_cols].to_parquet(params_path)
            logger.info("Gene params saved to %s", params_path)

    # Write adata.uns
    adata.uns["multivelo"] = {
        "max_iter": max_iter,
        "init_mode": init_mode,
        "model_to_run": model_to_run,
        "fit_decoupling": fit_decoupling,
        "n_anchors": n_anchors,
        "weight_c": weight_c,
        "likelihood_lower": likelihood_lower,
        "mean_likelihood": mean_likelihood,
        "model_distribution": model_distribution,
    }
    adata.uns["velocity"] = {
        "method": "multivelo",
        "velocity_key": "velo_s",
        "velocity_keys": ["velo_s", "velo_u", "velo_chrom"],
        "latent_time_key": None,
        "n_velocity_genes": n_velocity_genes,
        "fit_complete": True,
    }

    return VelocityResult(
        method="multivelo",
        n_velocity_genes=n_velocity_genes,
        velocity_key="velo_s",
        latent_time_key=None,
        model_distribution=model_distribution,
        mean_likelihood=mean_likelihood,
        params_path=params_path,
        metadata={
            "max_iter": max_iter,
            "init_mode": init_mode,
            "fit_decoupling": fit_decoupling,
            "weight_c": weight_c,
            "n_anchors": n_anchors,
        },
    )
