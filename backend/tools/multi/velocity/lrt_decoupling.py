"""Standalone epigenome–transcriptome coupling LRT via mv.LRT_decoupling.

Tests per-gene whether chromatin accessibility is significantly coupled to
transcription (Model 1) vs decoupled (Model 2), quantifying epigenome–
transcriptome coordination across the genome.

WARNING: LRT_decoupling calls recover_dynamics_chrom TWICE internally (once
with fit_decoupling=True, once with False). This is 2× the cost of
multi_velocity_recover_dynamics — expect 1–3 hours on a typical dataset.

Use the run_lrt=True flag in multi_velocity_downstream for integrated pipelines.
Use this standalone tool for targeted re-analysis with different thresholds,
or to re-run LRT without re-running the full downstream pipeline.
"""

from __future__ import annotations

import logging
from pathlib import Path

from backend.types import LRTResult

logger = logging.getLogger(__name__)


def run(
    adata,
    *,
    atac_h5ad_path: str | Path | None = None,
    lrt_pval_threshold: float = 0.05,
    output_dir: Path | None = None,
) -> LRTResult:
    """Test per-gene epigenome–transcriptome coupling with LRT_decoupling.

    Args:
        adata: RNA AnnData. Must have adata.var columns written by
               multi_velocity_recover_dynamics (fit_model, fit_likelihood,
               fit_likelihood_c). adata.uns["atac_h5ad_path"] used as
               fallback if atac_h5ad_path is not provided.
        atac_h5ad_path: Path to ATAC AnnData. Falls back to
                        adata.uns["atac_h5ad_path"].
        lrt_pval_threshold: p-value cutoff (pval_c column) for classifying
                            a gene as decoupled (default 0.05).
        output_dir: If provided, saves per-gene LRT statistics to
                    lrt_decoupling.parquet.

    Returns:
        LRTResult with n_genes_tested, n_decoupled, n_coupled, pct_decoupled,
        and lrt_table_path. LRT table also stored in adata.uns["lrt_decoupling"].

    LRT table columns (from mv.LRT_decoupling):
        likelihood_c_w_decoupled, likelihood_c_wo_decoupled,
        LRT_c, pval_c,
        likelihood_w_decoupled, likelihood_wo_decoupled,
        LRT, pval
    """
    for col in ("fit_model", "fit_likelihood", "fit_likelihood_c"):
        if col not in adata.var.columns:
            raise ValueError(
                f"adata.var['{col}'] not found. "
                "Run multi_velocity_recover_dynamics first."
            )

    atac_path = _resolve_atac_path(adata, atac_h5ad_path)
    return _run_lrt(
        adata,
        atac_path=atac_path,
        lrt_pval_threshold=lrt_pval_threshold,
        output_dir=Path(output_dir) if output_dir else None,
    )


from backend.tools.multi.velocity._utils import resolve_atac_path as _resolve_atac_path


def _run_lrt(
    adata,
    *,
    atac_path,
    lrt_pval_threshold,
    output_dir,
) -> LRTResult:
    import anndata as ad
    import multivelo as mv

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

    adata_atac = ad.read_h5ad(atac_path)

    logger.warning(
        "LRT_decoupling calls recover_dynamics_chrom twice internally. "
        "Expect 1–3 hours on a typical dataset."
    )
    logger.info("Running LRT_decoupling")

    # LRT_decoupling does NOT modify adata in-place — capture all three return values
    _, _, lrt_df = mv.LRT_decoupling(adata, adata_atac)

    adata.uns["lrt_decoupling"] = lrt_df.to_dict()

    n_tested = len(lrt_df)
    n_decoupled = int((lrt_df["pval_c"] < lrt_pval_threshold).sum())
    n_coupled = int((lrt_df["pval_c"] >= lrt_pval_threshold).sum())
    pct_decoupled = round(100.0 * n_decoupled / n_tested, 2) if n_tested > 0 else 0.0

    logger.info(
        "LRT complete: %d/%d genes decoupled (%.1f%%), pval_c threshold=%.3f",
        n_decoupled, n_tested, pct_decoupled, lrt_pval_threshold,
    )

    lrt_path = None
    if output_dir is not None:
        lrt_path = output_dir / "lrt_decoupling.parquet"
        lrt_df.to_parquet(lrt_path)
        logger.info("LRT table saved to %s", lrt_path)

    return LRTResult(
        n_genes_tested=n_tested,
        n_decoupled=n_decoupled,
        n_coupled=n_coupled,
        pct_decoupled=pct_decoupled,
        lrt_table_path=lrt_path,
        metadata={"pval_threshold": lrt_pval_threshold},
    )
