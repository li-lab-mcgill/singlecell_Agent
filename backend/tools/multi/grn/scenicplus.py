"""Enhancer-driven gene regulatory network inference using SCENIC+.

Orchestrates the SCENIC+ eRegulon inference workflow:
  1. Load RNA AnnData, CistopicObject, and menr dict from disk
  2. Create SCENICPLUS object
  3. Extract direct and extended cistromes from the menr dict
  4. Load TF→gene adjacencies into scplus_obj
  5. Store region→gene links
  6. Call build_grn() for direct cistromes, then for extended cistromes
     (build_grn takes DataFrames directly and returns List[eRegulon])
  7. Format eRegulons and serialize scplus_obj with dill

build_grn() API (actual):
    build_grn(tf_to_gene, region_to_gene, cistromes, is_extended, temp_dir, ...)
    → List[eRegulon]   (returns a list, does NOT modify scplus_obj in place)

Prerequisites:
  - atac_topic_pycisTopic  → adata.uns["cistopic_object_path"]
  - multi_grn_pycistarget  → adata.uns["pycistarget_menr_path"]
  - multi_grn_peak_to_gene → adata.uns["scenicplus_peak_gene_links"]
  - rna_grn_grnboost2      → adata.uns["grnboost2_adjacencies"]
"""

from __future__ import annotations

import logging
import pickle
import warnings
from pathlib import Path

import anndata
import numpy as np
import pandas as pd
import scipy.sparse as sp

from backend.types import eGRN

logger = logging.getLogger(__name__)


def run(
    adata,
    *,
    rna_h5ad_path: str | Path,
    cistopic_object_path: str | Path | None = None,
    pycistarget_menr_path: str | Path | None = None,
    tf_list_path: str | Path | None = None,
    coexpression_adj_path: str | Path | None = None,
    peak_gene_links_key: str = "scenicplus_peak_gene_links",
    min_target_genes: int = 10,
    min_regions_per_gene: int = 0,
    rho_threshold: float = 0.03,
    rho_dichotomize_tf2g: bool = True,
    rho_dichotomize_r2g: bool = True,
    rho_dichotomize_eregulon: bool = True,
    quantiles: tuple = (0.85, 0.90),
    top_n_regionTogenes_per_gene: tuple = (5, 10, 15),
    gsea_n_perm: int = 1000,
    run_aucell: bool = True,
    n_cpu: int = 4,
    output_dir: Path | None = None,
) -> eGRN:
    """Infer enhancer-driven eRegulons using SCENIC+.

    Args:
        adata: AnnData (ATAC). Must contain results from atac_topic_pycisTopic,
               multi_grn_pycistarget, multi_grn_peak_to_gene, and rna_grn_grnboost2.
        rna_h5ad_path: Path to the paired RNA AnnData (.h5ad).
        cistopic_object_path: Path to the pickled CistopicObject. If None, reads
                              from adata.uns["cistopic_object_path"].
        pycistarget_menr_path: Path to menr.pkl saved by multi_grn_pycistarget.
                                If None, reads from adata.uns["pycistarget_menr_path"].
        tf_list_path: Path to TF names file (allTFs_hg38.txt). Required when
                      coexpression_adj_path="recompute".
        coexpression_adj_path: Path to GRNBoost2 adjacency file (TSV). If None,
                               uses adata.uns["grnboost2_adjacencies"]. Pass
                               "recompute" to recompute TF→gene within SCENIC+.
        peak_gene_links_key: adata.uns key for peak-gene DataFrame from
                             multi_grn_peak_to_gene (default 'scenicplus_peak_gene_links').
        min_target_genes: Minimum target genes per eRegulon (default 10).
        min_regions_per_gene: Minimum regulatory regions per gene (default 0).
        rho_threshold: Spearman rho cutoff for activating/repressing split (default 0.03).
        rho_dichotomize_tf2g: Split TF→gene edges by rho sign (default True).
        rho_dichotomize_r2g: Split region→gene edges by rho sign (default True).
        rho_dichotomize_eregulon: Split eRegulons by rho sign (default True).
        quantiles: Quantile thresholds for region-to-gene importance cutoff (default (0.85, 0.90)).
        top_n_regionTogenes_per_gene: Top-N region-to-gene links per gene (default (5, 10, 15)).
        gsea_n_perm: GSEA permutations for eRegulon significance (default 1000).
        run_aucell: If True, run AUCell scoring after eRegulon inference (default True).
        n_cpu: Number of joblib workers for build_grn (default 4).
        output_dir: Directory for scplus_obj pickle and temporary files.

    Returns:
        eGRN result. eRegulon metadata stored in adata.uns["scenicplus_eregulons"].
        Full SCENICPLUS object path in adata.uns["scenicplus_object_path"].
    """
    # Resolve artifact paths from adata.uns if not explicitly provided
    if cistopic_object_path is None:
        assert "cistopic_object_path" in adata.uns, (
            "cistopic_object_path not provided and adata.uns['cistopic_object_path'] "
            "not found. Run atac_topic_pycisTopic with output_dir set first."
        )
        cistopic_object_path = adata.uns["cistopic_object_path"]

    if pycistarget_menr_path is None:
        assert "pycistarget_menr_path" in adata.uns, (
            "pycistarget_menr_path not provided and adata.uns['pycistarget_menr_path'] "
            "not found. Run multi_grn_pycistarget with output_dir set first."
        )
        pycistarget_menr_path = adata.uns["pycistarget_menr_path"]

    assert peak_gene_links_key in adata.uns, (
        f"adata.uns['{peak_gene_links_key}'] not found. "
        "Run multi_grn_peak_to_gene first."
    )
    assert Path(cistopic_object_path).exists(), (
        f"CistopicObject not found at {cistopic_object_path}."
    )
    assert Path(pycistarget_menr_path).exists(), (
        f"pycistarget menr.pkl not found at {pycistarget_menr_path}."
    )

    return _run_scenicplus(
        adata,
        rna_h5ad_path=Path(rna_h5ad_path),
        cistopic_object_path=Path(cistopic_object_path),
        pycistarget_menr_path=Path(pycistarget_menr_path),
        tf_list_path=Path(tf_list_path) if tf_list_path else None,
        coexpression_adj_path=(
            coexpression_adj_path
            if coexpression_adj_path == "recompute"
            else (Path(coexpression_adj_path) if coexpression_adj_path else None)
        ),
        peak_gene_links_key=peak_gene_links_key,
        min_target_genes=min_target_genes,
        min_regions_per_gene=min_regions_per_gene,
        rho_threshold=rho_threshold,
        rho_dichotomize_tf2g=rho_dichotomize_tf2g,
        rho_dichotomize_r2g=rho_dichotomize_r2g,
        rho_dichotomize_eregulon=rho_dichotomize_eregulon,
        quantiles=quantiles,
        top_n_regionTogenes_per_gene=top_n_regionTogenes_per_gene,
        gsea_n_perm=gsea_n_perm,
        run_aucell=run_aucell,
        n_cpu=n_cpu,
        output_dir=Path(output_dir) if output_dir else None,
    )


def _extract_cistromes_from_menr(
    menr: dict,
    scplus_regions: set,
    direct_annotation: list[str] = ("Direct_annot",),
    extended_annotation: list[str] = ("Orthology_annot",),
):
    """Extract direct and extended cistromes from old-style menr dict (pkl format).

    The menr dict from run_pycistarget has structure:
        {outer_key: {annotation_name: CisTargetResult}}
    where CisTargetResult has .cistromes = {TF_name: [region, ...]}

    Returns (direct_cistromes_adata, extended_cistromes_adata)
    """
    all_direct: dict[str, set] = {}   # TF -> set of regions
    all_extended: dict[str, set] = {} # TF -> set of regions

    for outer_key, annotation_dict in menr.items():
        if not isinstance(annotation_dict, dict):
            continue
        for annot_name, result in annotation_dict.items():
            is_direct = any(a in annot_name for a in direct_annotation)
            is_extended = any(a in annot_name for a in extended_annotation)
            if not (is_direct or is_extended):
                continue

            target_dict = all_direct if is_direct else all_extended

            # New-style pycistarget: result.cistromes = {TF: [regions]}
            if hasattr(result, "cistromes") and isinstance(result.cistromes, dict):
                for tf, regions in result.cistromes.items():
                    filtered = set(regions) & scplus_regions
                    if filtered:
                        target_dict.setdefault(tf, set()).update(filtered)
            # Fallback: try to use get_TF_list / get_motifs_per_TF from pycistarget utils
            elif hasattr(result, "motif_enrichment"):
                try:
                    from pycistarget.utils import get_TF_list, get_motifs_per_TF
                    tfs = get_TF_list(
                        motif_enrichment_table=result.motif_enrichment,
                        annotation=[annot_name.split("_annot")[0] + "_annot"]
                        if "_annot" in annot_name else list(direct_annotation),
                    )
                    for tf in tfs:
                        regions = set()
                        motifs = get_motifs_per_TF(
                            motif_enrichment_table=result.motif_enrichment,
                            tf=tf,
                            motif_column="Index",
                            annotation=[annot_name.split("_annot")[0] + "_annot"]
                            if "_annot" in annot_name else list(direct_annotation),
                        )
                        # If motif_hits available on result use it
                        if hasattr(result, "motif_hits"):
                            for motif in motifs:
                                if motif in result.motif_hits:
                                    regions.update(result.motif_hits[motif])
                        filtered = regions & scplus_regions
                        if filtered:
                            target_dict.setdefault(tf, set()).update(filtered)
                except Exception as exc:
                    logger.warning(
                        "Could not extract cistromes from %s/%s: %s",
                        outer_key, annot_name, exc,
                    )

    if not all_direct and not all_extended:
        raise RuntimeError(
            "No cistromes could be extracted from the menr dict. "
            "The pycistarget result objects may not have a .cistromes attribute. "
            "Check that pycistarget ran successfully and that annotation names "
            f"contain one of {list(direct_annotation)} or {list(extended_annotation)}."
        )

    return (
        _cistromes_dict_to_adata(all_direct, is_extended=False),
        _cistromes_dict_to_adata(all_extended, is_extended=True),
    )


def _cistromes_dict_to_adata(cistromes: dict[str, set], *, is_extended: bool):
    """Convert {TF: set_of_regions} to an AnnData (regions × TFs, bool X)."""
    if not cistromes:
        return anndata.AnnData(
            X=sp.csc_matrix((0, 0), dtype=bool),
            obs=pd.DataFrame(),
            var=pd.DataFrame(),
        )
    tf_names = sorted(cistromes.keys())
    all_regions = sorted(set.union(*cistromes.values()))
    region_index = {r: i for i, r in enumerate(all_regions)}
    matrix = np.zeros((len(all_regions), len(tf_names)), dtype=bool)
    for j, tf in enumerate(tf_names):
        for region in cistromes[tf]:
            if region in region_index:
                matrix[region_index[region], j] = True
    adata = anndata.AnnData(
        X=sp.csc_matrix(matrix),
        obs=pd.DataFrame(index=all_regions),
        var=pd.DataFrame(index=tf_names),
    )
    adata.var["is_extended"] = is_extended
    return adata


def _run_scenicplus(
    adata,
    *,
    rna_h5ad_path,
    cistopic_object_path,
    pycistarget_menr_path,
    tf_list_path,
    coexpression_adj_path,
    peak_gene_links_key,
    min_target_genes,
    min_regions_per_gene,
    rho_threshold,
    rho_dichotomize_tf2g,
    rho_dichotomize_r2g,
    rho_dichotomize_eregulon,
    quantiles,
    top_n_regionTogenes_per_gene,
    gsea_n_perm,
    run_aucell,
    n_cpu,
    output_dir,
) -> eGRN:
    import dill
    import scanpy as sc
    from scenicplus.scenicplus_class import create_SCENICPLUS_object
    from scenicplus.grn_builder.gsea_approach import build_grn
    from scenicplus.utils import format_egrns
    from scenicplus.eregulon_enrichment import get_eRegulons_as_signatures

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = str(output_dir / "scenicplus_tmp") if output_dir else "/tmp/scenicplus_tmp"
    Path(temp_dir).mkdir(parents=True, exist_ok=True)

    # --- Step 1: Load inputs ---
    logger.info("Loading RNA AnnData from %s", rna_h5ad_path)
    rna_adata = sc.read_h5ad(rna_h5ad_path)

    logger.info("Loading CistopicObject from %s", cistopic_object_path)
    with open(cistopic_object_path, "rb") as f:
        cisTopic_obj = pickle.load(f)

    logger.info("Loading pycistarget menr dict from %s", pycistarget_menr_path)
    with open(pycistarget_menr_path, "rb") as f:
        menr = dill.load(f)

    # --- Step 2: Construct SCENICPLUS object ---
    logger.info("Constructing SCENICPLUS object")
    scplus_obj = create_SCENICPLUS_object(
        GEX_anndata=rna_adata,
        cisTopic_obj=cisTopic_obj,
        menr=menr,
        multi_ome_mode=True,
    )

    # --- Step 3: Extract cistromes from menr ---
    logger.info("Extracting cistromes from menr dict")
    scplus_regions = set(adata.var_names)
    direct_cistromes, extended_cistromes = _extract_cistromes_from_menr(
        menr, scplus_regions=scplus_regions,
    )
    logger.info(
        "Cistromes: %d direct TFs, %d extended TFs",
        direct_cistromes.n_vars, extended_cistromes.n_vars,
    )

    # --- Step 4: Load TF→gene adjacencies ---
    if coexpression_adj_path == "recompute":
        assert tf_list_path is not None, (
            "tf_list_path is required when coexpression_adj_path='recompute'"
        )
        logger.info("Recomputing TF→gene relationships")
        from scenicplus.TF_to_gene import calculate_TFs_to_genes_relationships
        all_tfs = list(
            {*direct_cistromes.var_names, *extended_cistromes.var_names}
            & set(rna_adata.var_names)
        )
        gex_df = pd.DataFrame(
            rna_adata.X.toarray() if sp.issparse(rna_adata.X) else rna_adata.X,
            index=rna_adata.obs_names,
            columns=rna_adata.var_names,
        )
        tf2g_adj = calculate_TFs_to_genes_relationships(
            df_exp_mtx=gex_df,
            tf_names=all_tfs,
            temp_dir=Path(temp_dir),
            method="GBM",
            n_cpu=n_cpu,
        )
        scplus_obj.uns["TF2G_adj"] = tf2g_adj
    else:
        from scenicplus.TF_to_gene import load_TF2G_adj_from_file

        if coexpression_adj_path is not None and Path(coexpression_adj_path).exists():
            adj_file = coexpression_adj_path
        else:
            # Write GRNBoost2 in-memory adjacencies to TSV
            assert "grnboost2_adjacencies" in adata.uns, (
                "grnboost2_adjacencies not in adata.uns and coexpression_adj_path not set. "
                "Run rna_grn_grnboost2 first."
            )
            adj_df = pd.DataFrame(adata.uns["grnboost2_adjacencies"])
            adj_file = (
                Path(output_dir) / "grnboost2_adj.tsv"
                if output_dir else Path("/tmp/grnboost2_adj.tsv")
            )
            adj_df.to_csv(adj_file, sep="\t", index=False)
            logger.info("GRNBoost2 adjacencies written to %s", adj_file)

        logger.info("Loading TF→gene adjacencies from %s", adj_file)
        load_TF2G_adj_from_file(
            scplus_obj,
            f_adj=str(adj_file),
            inplace=True,
            key="TF2G_adj",
        )

    tf2g_df = scplus_obj.uns["TF2G_adj"]

    # --- Step 5: Region→gene links ---
    r2g_df = adata.uns[peak_gene_links_key]
    scplus_obj.uns["region_to_gene"] = r2g_df
    logger.info("Loaded %d region-to-gene links", len(r2g_df))

    # --- Step 6: Build eGRN — call build_grn twice (direct + extended) ---
    # build_grn takes DataFrames directly; does NOT take scplus_obj
    # Returns List[eRegulon]; temp_dir is required
    build_grn_kwargs = dict(
        tf_to_gene=tf2g_df,
        region_to_gene=r2g_df,
        temp_dir=temp_dir,
        order_regions_to_genes_by="importance",
        order_TFs_to_genes_by="importance",
        gsea_n_perm=gsea_n_perm,
        quantiles=quantiles,
        top_n_regionTogenes_per_gene=top_n_regionTogenes_per_gene,
        min_regions_per_gene=min_regions_per_gene,
        rho_dichotomize_tf2g=rho_dichotomize_tf2g,
        rho_dichotomize_r2g=rho_dichotomize_r2g,
        rho_dichotomize_eregulon=rho_dichotomize_eregulon,
        rho_threshold=rho_threshold,
        NES_thr=0,
        adj_pval_thr=1,
        min_target_genes=min_target_genes,
        merge_eRegulons=True,
        n_cpu=n_cpu,
    )

    all_eregulons = []
    if direct_cistromes.n_vars > 0:
        logger.info(
            "Building direct eGRN (is_extended=False, %d TFs)", direct_cistromes.n_vars
        )
        direct_eregulons = build_grn(
            cistromes=direct_cistromes,
            is_extended=False,
            **build_grn_kwargs,
        )
        all_eregulons.extend(direct_eregulons)
        logger.info("Direct eRegulons: %d", len(direct_eregulons))
    else:
        logger.warning("No direct cistromes found — skipping direct eGRN build")

    if extended_cistromes.n_vars > 0:
        logger.info(
            "Building extended eGRN (is_extended=True, %d TFs)", extended_cistromes.n_vars
        )
        extended_eregulons = build_grn(
            cistromes=extended_cistromes,
            is_extended=True,
            **build_grn_kwargs,
        )
        all_eregulons.extend(extended_eregulons)
        logger.info("Extended eRegulons: %d", len(extended_eregulons))
    else:
        logger.warning("No extended cistromes found — skipping extended eGRN build")

    if not all_eregulons:
        warnings.warn(
            "build_grn produced no eRegulons for either direct or extended cistromes. "
            "Check input data quality, motif enrichment results, and region-to-gene links.",
            UserWarning, stacklevel=2,
        )

    # Store eRegulons in scplus_obj for format_egrns
    scplus_obj.uns["eRegulons"] = all_eregulons

    # --- Step 7: Format eRegulons → metadata DataFrame ---
    logger.info("Formatting %d eRegulons", len(all_eregulons))
    format_egrns(
        scplus_obj,
        eregulons_key="eRegulons",
        TF2G_key="TF2G_adj",
        key_added="eRegulon_metadata",
    )
    eregulon_df = scplus_obj.uns.get("eRegulon_metadata", pd.DataFrame())
    adata.uns["scenicplus_eregulons"] = eregulon_df

    # --- Step 8: Serialize scplus_obj (must use dill) ---
    if output_dir is not None:
        scplus_obj_path = output_dir / "scplus_obj.pkl"
        with open(scplus_obj_path, "wb") as f:
            dill.dump(scplus_obj, f)
        adata.uns["scenicplus_object_path"] = str(scplus_obj_path)
        logger.info("SCENICPLUS object saved to %s", scplus_obj_path)
    else:
        warnings.warn(
            "output_dir not set — SCENICPLUS object not saved. "
            "multi_grn_scenicplus_aucell requires adata.uns['scenicplus_object_path'].",
            UserWarning, stacklevel=2,
        )

    # --- Step 9: Optional AUCell scoring ---
    if run_aucell and len(eregulon_df) > 0:
        logger.info("Running AUCell scoring on eRegulons")
        _score_aucell(adata, rna_adata, eregulon_df, auc_threshold=0.05, n_cpu=n_cpu)

    # Build return value
    if len(eregulon_df) > 0:
        n_eregulons = eregulon_df["Region_signature_name"].nunique() if "Region_signature_name" in eregulon_df.columns else len(eregulon_df)
        n_tfs = eregulon_df["Gene_signature_name"].str.split("_").str[0].nunique() if "Gene_signature_name" in eregulon_df.columns else 0
        n_regions = eregulon_df["Region"].nunique() if "Region" in eregulon_df.columns else 0
        n_targets = eregulon_df["Gene"].nunique() if "Gene" in eregulon_df.columns else 0
    else:
        n_eregulons = n_tfs = n_regions = n_targets = 0

    logger.info(
        "SCENIC+ complete: %d eRegulons, %d TFs, %d regions, %d target genes",
        n_eregulons, n_tfs, n_regions, n_targets,
    )

    return eGRN(
        n_eregulons=n_eregulons,
        n_tfs=n_tfs,
        n_regions=n_regions,
        n_target_genes=n_targets,
        eregulons_key="scenicplus_eregulons",
        metadata={
            "min_target_genes": min_target_genes,
            "rho_threshold": rho_threshold,
            "quantiles": list(quantiles),
            "top_n_regionTogenes_per_gene": list(top_n_regionTogenes_per_gene),
            "scenicplus_object_path": adata.uns.get("scenicplus_object_path"),
            "aucell_run": run_aucell,
        },
    )


def _score_aucell(adata, rna_adata, eregulon_df, *, auc_threshold: float, n_cpu: int) -> None:
    """Run AUCell using score_eRegulons(eRegulons_df, gex_mtx, acc_mtx, ...)."""
    from scenicplus.eregulon_enrichment import score_eRegulons

    # Verify barcode alignment between RNA and ATAC before storing RNA AUC on ATAC adata
    if list(rna_adata.obs_names) != list(adata.obs_names):
        raise ValueError(
            f"Barcode mismatch: RNA adata has {rna_adata.n_obs} cells, "
            f"ATAC adata has {adata.n_obs} cells, and their obs_names differ. "
            "Ensure both AnnDatas are aligned (same cells, same order) before running SCENIC+."
        )

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

    auc_result = score_eRegulons(
        eRegulons=eregulon_df,
        gex_mtx=gex_df,
        acc_mtx=acc_df,
        auc_threshold=auc_threshold,
        n_cpu=n_cpu,
    )

    rna_auc_df = auc_result["Gene_based"]
    atac_auc_df = auc_result["Region_based"]

    adata.obsm["X_scenicplus_atac_auc"] = atac_auc_df.values
    adata.obsm["X_scenicplus_rna_auc"] = rna_auc_df.values
    adata.uns["scenicplus_auc_regulon_names"] = list(rna_auc_df.columns)
    logger.info(
        "AUCell complete: %d eRegulons scored across %d cells",
        rna_auc_df.shape[1], rna_auc_df.shape[0],
    )
