"""Post-fitting velocity analysis: graph, latent time, and optional LRT.

Fast downstream steps after multi_velocity_recover_dynamics (or rna_velocity_scvelo):
  1. Velocity transition probability graph (mv.velocity_graph)
  2. Global pseudotime / latent time (mv.latent_time)
  3. Optional: epigenome–transcriptome decoupling LRT (mv.LRT_decoupling)

Steps 1–2 are fast and can be re-run with different parameters without
re-running the expensive fitting step.

WARNING: run_lrt=True is expensive — LRT_decoupling calls recover_dynamics_chrom
twice internally (with and without fit_decoupling), effectively doubling the
fitting cost. Expect 1–3 hours on a typical dataset. Default is False.
"""

from __future__ import annotations

import logging
from pathlib import Path

from backend.types import VelocityDownstreamResult

logger = logging.getLogger(__name__)


def run(
    adata,
    *,
    atac_h5ad_path: str | Path | None = None,
    velocity_key: str | None = None,
    compute_latent_time: bool = True,
    run_lrt: bool = False,
    lrt_pval_threshold: float = 0.05,
    output_dir: Path | None = None,
) -> VelocityDownstreamResult:
    """Compute velocity graph, latent time, and optionally run LRT.

    Args:
        adata: AnnData with fitted velocity layers (from multi_velocity_recover_dynamics
               or rna_velocity_scvelo).
        atac_h5ad_path: Path to ATAC AnnData. Required only if run_lrt=True. Falls
                        back to adata.uns["atac_h5ad_path"].
        velocity_key: Velocity layer to use for graph and latent time. If None,
                      read from adata.uns["velocity"]["velocity_key"] (auto-wired
                      by executor from the upstream fitting tool).
        compute_latent_time: Infer global pseudotime from velocity (default True).
        run_lrt: Run LRT_decoupling to test per-gene epigenome–transcriptome coupling
                 (default False — extremely expensive, see module docstring).
        lrt_pval_threshold: p-value cutoff for classifying genes as decoupled
                            (pval_c < threshold) vs coupled (default 0.05).
        output_dir: If run_lrt=True and output_dir is provided, saves LRT table to
                    lrt_decoupling.parquet.

    Returns:
        VelocityDownstreamResult with velocity_key, n_velocity_genes_graph,
        latent_time_key, and optional LRT gene counts.
    """
    vkey = _resolve_velocity_key(adata, velocity_key)

    if vkey not in adata.layers:
        raise ValueError(
            f"Velocity layer '{vkey}' not found in adata.layers. "
            f"Run multi_velocity_recover_dynamics or rna_velocity_scvelo first. "
            f"Available layers: {list(adata.layers.keys())}"
        )

    return _run_downstream(
        adata,
        vkey=vkey,
        atac_h5ad_path=atac_h5ad_path,
        compute_latent_time=compute_latent_time,
        run_lrt=run_lrt,
        lrt_pval_threshold=lrt_pval_threshold,
        output_dir=Path(output_dir) if output_dir else None,
    )


def _resolve_velocity_key(adata, velocity_key) -> str:
    if velocity_key is not None:
        return velocity_key
    vk = adata.uns.get("velocity", {}).get("velocity_key")
    if vk is None:
        raise ValueError(
            "velocity_key not provided and adata.uns['velocity']['velocity_key'] not set. "
            "Run multi_velocity_recover_dynamics or rna_velocity_scvelo first."
        )
    return vk


def _run_downstream(
    adata,
    *,
    vkey,
    atac_h5ad_path,
    compute_latent_time,
    run_lrt,
    lrt_pval_threshold,
    output_dir,
) -> VelocityDownstreamResult:
    import multivelo as mv
    import pandas as pd

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

    method = adata.uns.get("velocity", {}).get("method", "multivelo")

    # Step 1: velocity transition probability graph
    logger.info("Computing velocity graph (vkey='%s', method='%s')", vkey, method)
    if method == "scvelo":
        import scvelo as scv
        scv.tl.velocity_graph(adata)
    else:
        mv.velocity_graph(adata, vkey=vkey, xkey="Ms")

    # Step 2: latent time
    latent_time_key = None
    if compute_latent_time:
        logger.info("Computing latent time")
        if method == "scvelo":
            scv.tl.latent_time(adata)
        else:
            mv.latent_time(adata, vkey=vkey)
        latent_time_key = "latent_time"
        adata.uns.setdefault("velocity", {})["latent_time_key"] = latent_time_key
        logger.info("Latent time written to adata.obs['latent_time']")

    # Step 3: optional LRT
    n_decoupled = None
    n_coupled = None
    if run_lrt:
        import anndata as ad

        atac_path = atac_h5ad_path or adata.uns.get("atac_h5ad_path")
        if atac_path is None:
            raise ValueError(
                "atac_h5ad_path required for run_lrt=True. "
                "Provide it as a parameter or run multi_qc_intersect first."
            )
        atac_path = Path(atac_path)
        if not atac_path.exists():
            raise FileNotFoundError(f"ATAC AnnData not found: {atac_path}")

        logger.warning(
            "run_lrt=True: LRT_decoupling calls recover_dynamics_chrom twice internally "
            "(with and without fit_decoupling). Expect 1–3 hours on a typical dataset."
        )
        adata_atac = ad.read_h5ad(atac_path)
        _, _, lrt_df = mv.LRT_decoupling(adata, adata_atac)

        adata.uns["lrt_decoupling"] = lrt_df.to_dict()
        n_decoupled = int((lrt_df["pval_c"] < lrt_pval_threshold).sum())
        n_coupled = int((lrt_df["pval_c"] >= lrt_pval_threshold).sum())
        logger.info(
            "LRT complete: %d decoupled, %d coupled (pval_c threshold=%.3f)",
            n_decoupled, n_coupled, lrt_pval_threshold,
        )

        if output_dir is not None:
            lrt_path = output_dir / "lrt_decoupling.parquet"
            lrt_df.to_parquet(lrt_path)
            logger.info("LRT table saved to %s", lrt_path)

    # n_velocity_genes_graph: read from velo_s_genes flag set by set_velocity_genes()
    n_velocity_genes_graph = int(
        adata.var.get("velo_s_genes", pd.Series(dtype=bool)).sum()
    )

    return VelocityDownstreamResult(
        velocity_key=vkey,
        n_velocity_genes_graph=n_velocity_genes_graph,
        latent_time_key=latent_time_key,
        lrt_n_decoupled=n_decoupled,
        lrt_n_coupled=n_coupled,
        metadata={"lrt_pval_threshold": lrt_pval_threshold if run_lrt else None},
    )
