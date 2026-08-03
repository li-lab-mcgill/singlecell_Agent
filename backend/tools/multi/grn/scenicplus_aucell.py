"""eRegulon AUCell scoring for SCENIC+ (standalone re-scoring tool).

Re-scores eRegulons from a previously-run multi_grn_scenicplus without
re-running eRegulon inference. Useful for testing different AUC thresholds
or computing Regulon Specificity Scores (RSS) per cell type.

score_eRegulons() API (actual):
    score_eRegulons(eRegulons, gex_mtx, acc_mtx, auc_threshold, normalize, n_cpu)
    → {"Gene_based": DataFrame, "Region_based": DataFrame}

No make_rankings() call is needed — ranking is handled internally.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import scipy.sparse as sp

from backend.types import eGRN

logger = logging.getLogger(__name__)


def run(
    adata,
    *,
    rna_adata=None,
    rna_h5ad_path: str | Path | None = None,
    eregulons_key: str = "scenicplus_eregulons",
    scplus_obj_key: str = "scenicplus_object_path",
    auc_threshold: float = 0.05,
    celltype_key: str | None = None,
    n_cpu: int = 4,
    output_dir: Path | None = None,
) -> eGRN:
    """Re-score eRegulons with AUCell.

    score_eRegulons() takes DataFrames directly (cells × genes, cells × regions)
    and calls rank_data() internally — no separate make_rankings() step needed.

    Args:
        adata: AnnData (ATAC). Must contain adata.uns[eregulons_key] from
               multi_grn_scenicplus.
        rna_adata: Optional RNA AnnData object (cells × genes). If None,
                   rna_h5ad_path must be provided.
        rna_h5ad_path: Path to the paired RNA AnnData (.h5ad). Used if
                       rna_adata is None.
        eregulons_key: adata.uns key for the eRegulon metadata DataFrame
                       (default 'scenicplus_eregulons').
        scplus_obj_key: adata.uns key pointing to the dill pickle path
                        (default 'scenicplus_object_path'). Used only for
                        metadata — scoring uses DataFrames directly.
        auc_threshold: AUC threshold (default 0.05).
        celltype_key: adata.obs column for Regulon Specificity Score (RSS).
        n_cpu: Workers for AUCell (default 4).
        output_dir: Optional; not used for scoring (reserved for RSS output).

    Returns:
        eGRN result with AUC scores stored in:
          - adata.obsm["X_scenicplus_atac_auc"]: region-based AUC
          - adata.obsm["X_scenicplus_rna_auc"]: gene-based AUC
          - adata.uns["scenicplus_auc_regulon_names"]: eRegulon name list
          - adata.uns["scenicplus_rss"]: RSS DataFrame (if celltype_key set)
    """
    assert eregulons_key in adata.uns, (
        f"adata.uns['{eregulons_key}'] not found. "
        "Run multi_grn_scenicplus first."
    )

    if rna_adata is None:
        assert rna_h5ad_path is not None, (
            "Either rna_adata or rna_h5ad_path must be provided."
        )
        import scanpy as sc
        rna_adata = sc.read_h5ad(rna_h5ad_path)

    return _run_aucell(
        adata,
        rna_adata=rna_adata,
        eregulons_key=eregulons_key,
        auc_threshold=auc_threshold,
        celltype_key=celltype_key,
        n_cpu=n_cpu,
    )


def _run_aucell(
    adata,
    rna_adata,
    *,
    eregulons_key,
    auc_threshold,
    celltype_key,
    n_cpu,
) -> eGRN:
    from scenicplus.eregulon_enrichment import score_eRegulons

    eregulon_df = adata.uns[eregulons_key]

    # Build expression and accessibility DataFrames (cells × features)
    gex_df = pd.DataFrame(
        rna_adata.X.toarray() if sp.issparse(rna_adata.X) else rna_adata.X,
        index=rna_adata.obs_names,
        columns=rna_adata.var_names,
    )
    acc_df = pd.DataFrame(
        adata.X.toarray() if sp.issparse(adata.X) else adata.X,
        index=adata.obs_names,
        columns=adata.var_names,
    )

    # score_eRegulons handles ranking internally; returns {"Gene_based": df, "Region_based": df}
    logger.info("Scoring %d eRegulons across %d cells", len(eregulon_df), adata.n_obs)
    auc_result = score_eRegulons(
        eRegulons=eregulon_df,
        gex_mtx=gex_df,
        acc_mtx=acc_df,
        auc_threshold=auc_threshold,
        n_cpu=n_cpu,
    )

    rna_auc_df = auc_result["Gene_based"]
    atac_auc_df = auc_result["Region_based"]

    # obsm requires numpy arrays
    adata.obsm["X_scenicplus_atac_auc"] = atac_auc_df.values
    adata.obsm["X_scenicplus_rna_auc"] = rna_auc_df.values
    adata.uns["scenicplus_auc_regulon_names"] = list(rna_auc_df.columns)
    logger.info(
        "AUCell scoring complete: %d eRegulons × %d cells",
        rna_auc_df.shape[1], rna_auc_df.shape[0],
    )

    # Regulon Specificity Score per cell type
    if celltype_key is not None:
        if celltype_key in adata.obs.columns:
            logger.info("Computing RSS for '%s'", celltype_key)
            rss_df = _compute_rss(rna_auc_df, adata.obs[celltype_key])
            adata.uns["scenicplus_rss"] = rss_df
        else:
            logger.warning(
                "celltype_key='%s' not in adata.obs — skipping RSS", celltype_key
            )

    n_eregulons = rna_auc_df.shape[1]
    n_tfs = eregulon_df["Gene_signature_name"].str.split("_").str[0].nunique() if "Gene_signature_name" in eregulon_df.columns else 0
    n_regions = eregulon_df["Region"].nunique() if "Region" in eregulon_df.columns else 0
    n_targets = eregulon_df["Gene"].nunique() if "Gene" in eregulon_df.columns else 0

    return eGRN(
        n_eregulons=n_eregulons,
        n_tfs=n_tfs,
        n_regions=n_regions,
        n_target_genes=n_targets,
        eregulons_key=eregulons_key,
        metadata={
            "auc_threshold": auc_threshold,
            "n_cells_scored": rna_auc_df.shape[0],
            "rss_computed": celltype_key is not None and celltype_key in adata.obs.columns,
        },
    )


def _compute_rss(auc_df: pd.DataFrame, cell_types: pd.Series) -> pd.DataFrame:
    """Compute Regulon Specificity Score — (n_cell_types × n_regulons) matrix.

    For each (cell_type, regulon) pair, RSS = JSD between the mean AUC in that
    cell type vs all other cells, treating each regulon independently as a
    2-point distribution. Values closer to 1 indicate higher cell-type specificity.
    """
    import numpy as np

    cell_type_labels = cell_types.values
    unique_types = cell_types.unique()

    rss_records = {}
    for ct in unique_types:
        mask = cell_type_labels == ct
        # Mean AUC per regulon in this cell type vs all others (+ epsilon for stability)
        ct_auc = auc_df[mask].mean(axis=0).values + 1e-10   # (n_regulons,)
        bg_auc = auc_df[~mask].mean(axis=0).values + 1e-10  # (n_regulons,)
        # Per-regulon 2-point distribution: fraction of total mean in this cell type
        p = ct_auc / (ct_auc + bg_auc)
        p = np.clip(p, 1e-10, 1 - 1e-10)
        q = 1.0 - p
        # JSD between [p, 1-p] and [0.5, 0.5] (uniform = no specificity)
        rss = p * np.log2(p / 0.5) + q * np.log2(q / 0.5)  # (n_regulons,)
        rss_records[ct] = rss

    # Result: rows = cell types, columns = regulon names
    return pd.DataFrame(rss_records, index=auc_df.columns).T
