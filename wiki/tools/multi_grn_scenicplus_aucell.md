---
type: tool
id: multi_grn_scenicplus_aucell
modality: multi
stage: grn_inference
backend: backend/tools/multi/grn/scenicplus_aucell.py
label: eRegulon AUCell Scoring (SCENIC+)
default: false
params:
  auc_threshold: 0.05
  seed: 42
  n_cpu: 4
prerequisites:
  - multi_grn_scenicplus
---

Re-scores SCENIC+ eRegulons with AUCell without re-running eRegulon inference. Use this to test different `auc_threshold` values or compute Regulon Specificity Scores (RSS) per cell type.

## When to run this separately vs. inside `multi_grn_scenicplus`

`multi_grn_scenicplus` runs AUCell internally when `run_aucell=True` (default). Run this separate tool when:
- You want to change `auc_threshold` without rerunning eRegulon inference
- You want to compute RSS for a specific cell type annotation
- You want to re-score after updating the cell type labels in `adata.obs`

**This tool intentionally overwrites** `adata.obsm["X_scenicplus_rna_auc"]` and `adata.obsm["X_scenicplus_atac_auc"]` — that is the intended re-scoring pattern.

## AUCell scoring

`score_eRegulons()` is called **twice** (region-based and gene-based) and results accumulate under `scplus_obj.uns["eRegulon_AUC"]`. Both region and gene rankings are built fresh via `make_rankings()`.

## Regulon Specificity Score (RSS)

If `celltype_key` is provided and the column exists in `adata.obs`, RSS is computed as a Jensen-Shannon divergence measure of how specific each eRegulon is to each cell type. Stored in `adata.uns["scenicplus_rss"]`.

## Outputs stored in adata

| Key | Type | Description |
|-----|------|-------------|
| `adata.obsm["X_scenicplus_atac_auc"]` | ndarray | Region-based AUC scores (cells × eRegulons) |
| `adata.obsm["X_scenicplus_rna_auc"]` | ndarray | Gene-based AUC scores (cells × eRegulons) |
| `adata.uns["scenicplus_auc_regulon_names"]` | list | eRegulon name index |
| `adata.uns["scenicplus_rss"]` | DataFrame | RSS per cell type (only if celltype_key set) |

**Params:**
- `eregulons_key`: `adata.uns` key for the eRegulon metadata DataFrame (default `'scenicplus_eregulons'`); change if you stored eRegulons under a different key
- `scplus_obj_key`: `adata.uns` key pointing to the dill pickle path (default `'scenicplus_object_path'`); change if you used a non-standard key in `multi_grn_scenicplus`
- `auc_threshold`: AUC threshold for regulon activity — fraction of top-ranked genes/regions used to compute AUC (default 0.05)
- `celltype_key`: `adata.obs` column for RSS computation (default None); RSS not computed if omitted
- `seed`: random seed for AUCell tie-breaking (default 42)
- `n_cpu`: AUCell workers (default 4)

Package: [[packages/scenicplus]]
Method: [[methods/enhancer_grn]]
