---
type: tool
id: multi_grn_pycistarget
modality: multi
stage: grn_inference
backend: backend/tools/multi/grn/pycistarget.py
label: TF-Region Motif Enrichment (pycistarget)
default: false
params:
  species: null
  ctx_auc_threshold: 0.005
  ctx_nes_threshold: 3.0
  ctx_rank_threshold: 0.05
  dem_log2fc_thr: 0.5
  dem_motif_hit_thr: 3.0
  annotation_version: v9
  n_cpu: 4
requires_resources:
  - resource: pyscenic_databases
    params: [ctx_db_path, motif_annotations_path]
    note: Same cisTarget feather databases used by rna_grn_pyscenic. No additional download needed if already present. annotation_version must match the database version (v10nr_clust for the standard preset).
prerequisites:
  - atac_topic_pycisTopic
---

Runs cisTarget TF-region motif enrichment on the topic region sets produced by `atac_topic_pycisTopic`. Uses the `run_pycistarget()` wrapper from SCENIC+ (`scenicplus.wrappers.run_pycistarget`).

**`species` is required** — it controls TSS annotation download from biomart for promoter exclusion during enrichment. Valid values: `'homo_sapiens'`, `'mus_musculus'`, `'drosophila_melanogaster'`, `'gallus_gallus'`.

## Database version

**`annotation_version` must match your database files.** The standard `pyscenic_databases` preset lists `mc9nr` feather files (v9-era) — the default `annotation_version='v9'` is correct for these. If you have downloaded separate `v10nr_clust` feather files, set `annotation_version='v10nr_clust'`. Setting the wrong version causes a silent annotation mismatch where TF names are looked up from the wrong annotation table.

## DEM method

Pass `dem_db_path` to enable the Differentially Enriched Motifs (DEM) method alongside cisTarget. Recommended for small region sets (< 500 regions) where ranking-based enrichment is unstable.

## Outputs stored in adata

| Key | Type | Description |
|-----|------|-------------|
| `adata.uns["pycistarget_menr_path"]` | str | Path to pickled menr dict (required by multi_grn_scenicplus) |
| `adata.uns["pycistarget_tf_region_links"]` | DataFrame | Merged TF-region enrichment summary |

## Prerequisite chain

Reads from `adata.uns["topic_region_sets"]` (produced by `atac_topic_pycisTopic`). The `menr` dict path is stored in `adata.uns` and consumed automatically by `multi_grn_scenicplus`.

**Params:**
- `species`: organism name for biomart TSS annotation (required)
- `ctx_db_path`: path to cisTarget ranking .feather database
- `motif_annotations_path`: path to motif-to-TF annotation .tbl file
- `dem_db_path`: path to DEM database (None = DEM disabled)
- `annotation_version`: must match database version (`v9` default; use `v10nr_clust` for standard preset)
- `ctx_rank_threshold`: fraction of top-ranked regions (0.05 = top 5%, **not** an absolute count)
- `dem_motif_hit_thr`: minimum motif hit score for DEM (default 3.0); increase to reduce false positives in DEM mode
- `dem_max_bg_regions`: maximum background regions sampled for DEM comparison (default 500)
- `annotation_version`: **must match your database files** — use `'v9'` (default) for `mc9nr` files (the standard preset); use `'v10nr_clust'` only if you have v10nr_clust feather files; wrong version causes silent annotation mismatch

Package: [[packages/pycistarget]]
Resources: [[resources/pyscenic_databases]]
