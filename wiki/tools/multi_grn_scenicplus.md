---
type: tool
id: multi_grn_scenicplus
modality: multi
stage: grn_inference
backend: backend/tools/multi/grn/scenicplus.py
label: Enhancer-driven eGRN Inference (SCENIC+)
default: false
params:
  min_target_genes: 10
  min_regions_per_gene: 0
  rho_threshold: 0.05
  quantiles: [0.85, 0.90, 0.95]
  top_n_regionTogenes_per_gene: [5, 10, 15]
  gsea_n_perm: 1000
  run_aucell: true
  n_cpu: 4
requires_resources:
  - resource: pyscenic_databases
    note: Same files as rna_grn_pyscenic. tf_list_path needed for TF→gene step.
prerequisites:
  - atac_topic_pycisTopic
  - multi_grn_pycistarget
  - multi_grn_peak_to_gene
  - rna_grn_grnboost2
---

Orchestrates the complete SCENIC+ eRegulon inference pipeline. Produces eRegulons: `(TF, regulatory_regions, target_genes)` triplets with activating/repressing directionality and multi-modal evidence.

## Five-step workflow

1. **Load inputs** — reads RNA AnnData, menr dict (from `multi_grn_pycistarget`), TF→gene adjacencies, and region→gene links into DataFrames
2. **Extract cistromes** — parses the menr pkl's CisTargetResult objects (`.cistromes` attribute) to build two AnnDatas: direct cistromes and extended cistromes (each: regions × TFs with boolean values); **must be built separately** — `build_grn` is called once per cistrome set
3. **Load TF→gene adjacencies** — from `adata.uns["grnboost2_adjacencies"]` (or `coexpression_adj_path`); alternatively recomputes with `coexpression_adj_path="recompute"` using SCENIC+'s `calculate_TFs_to_genes_relationships()`
4. **Load region→gene links** — from `adata.uns["scenicplus_peak_gene_links"]` (from `multi_grn_peak_to_gene`); loaded as a DataFrame
5. **Build eGRN** — `build_grn(tf_to_gene, region_to_gene, cistromes, is_extended, ...)` from `scenicplus.grn_builder.gsea_approach`; called **twice** (direct then extended); results concatenated into final eRegulon list

## Serialization

The merged eRegulon DataFrame is stored in `adata.uns["scenicplus_eregulons"]`. No SCENICPLUS object is serialized — `multi_grn_scenicplus_aucell` reads the eRegulon DataFrame and input matrices directly from the AnnDatas.

## AUCell

If `run_aucell=True` (default), AUCell scoring is run automatically after inference. Results are stored in `adata.obsm["X_scenicplus_rna_auc"]` and `adata.obsm["X_scenicplus_atac_auc"]`. To re-score with different thresholds, run `multi_grn_scenicplus_aucell` (which overwrites these keys intentionally).

## Outputs stored in adata

| Key | Type | Description |
|-----|------|-------------|
| `adata.uns["scenicplus_eregulons"]` | DataFrame | eRegulon metadata (columns: Region_signature_name, Region, Gene_signature_name, Gene, importance, rho) |
| `adata.obsm["X_scenicplus_rna_auc"]` | ndarray | Gene-based AUC scores (if run_aucell=True) |
| `adata.obsm["X_scenicplus_atac_auc"]` | ndarray | Region-based AUC scores (if run_aucell=True) |
| `adata.uns["scenicplus_auc_regulon_names"]` | list | eRegulon name index for obsm columns |

**Params:**
- `rna_h5ad_path`: path to paired RNA AnnData (required)
- `tf_list_path`: TF names file (allTFs_hg38.txt) — used for internal TF→gene recomputation
- `coexpression_adj_path`: GRNBoost2 adj file path, or `"recompute"` to use SCENIC+'s internal scorer
- `n_cpu`: joblib parallelism workers for `build_grn` and `calculate_TFs_to_genes_relationships` (default 4)
- `rho_threshold`: Spearman rho cutoff for activating/repressing split (single float applied across all link types, default 0.05)
- `rho_dichotomize_tf2g`: split TF→gene edges into activating/repressing by rho sign (default True); set False to keep unsigned TF→gene links
- `rho_dichotomize_r2g`: split region→gene edges by rho sign (default True)
- `rho_dichotomize_eregulon`: split final eRegulons by rho sign (default True); all three dichotomize flags can be set independently
- `quantiles`: quantile thresholds for region-to-gene importance cutoff in `build_grn` (default `[0.85, 0.90, 0.95]`); multiple values generate multiple candidate eRegulon sets that are then merged
- `top_n_regionTogenes_per_gene`: top-N region-to-gene links per gene to retain per threshold (default `[5, 10, 15]`); paired with `quantiles`
- `gsea_n_perm`: GSEA permutations for eRegulon significance assessment (default 1000; reduce to 500 to speed up large runs)
- `coexpression_adj_path`: GRNBoost2 adjacency file path (TSV/parquet); if None, uses `adata.uns["grnboost2_adjacencies"]` written to a temp TSV; pass `"recompute"` (string sentinel) to ignore GRNBoost2 entirely and run SCENIC+'s internal `calculate_TFs_to_genes_relationships()` instead

Package: [[packages/scenicplus]]
Method: [[methods/enhancer_grn]]
Resources: [[resources/pyscenic_databases]]
