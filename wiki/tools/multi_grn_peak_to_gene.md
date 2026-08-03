---
type: tool
id: multi_grn_peak_to_gene
modality: multi
stage: grn_inference
backend: backend/tools/multi/grn/peak_to_gene.py
label: Peak-to-Gene Correlation (SCENIC+ style)
default: false
params:
  species: homo_sapiens
  search_space_upstream: [1000, 150000]
  search_space_downstream: [1000, 150000]
  search_space_extend_tss: [10, 10]
  importance_threshold: 0.05
  rho_threshold: 0.03
  importance_scoring_method: GBM
  n_cpu: 4
prerequisites:
  - atac_peak_calling_macs2 or atac_peak_calling_macs3
---

Computes SCENIC+-style peak-to-gene regulatory links for use in eRegulon inference. This tool is **not** the same as `atac_peak_to_gene_correlation` and produces a different output schema.

Two sequential steps:
1. **Define search space** (`get_search_space`): candidate peak-gene pairs within ±150kb of TSS (configurable)
2. **Score links** (`calculate_regions_to_genes_relationships`): random forest importance + Spearman correlation; post-hoc filtering by `importance_threshold` and `rho_threshold`

## Why separate from `atac_peak_to_gene_correlation`

| Aspect | This tool | `atac_peak_to_gene_correlation` |
|---|---|---|
| Window | ±150kb from TSS (tuple min/max) | 500kb flat |
| Correlation | Spearman + RF importance | Pearson |
| Output key | `scenicplus_peak_gene_links` | `peak_gene_links` |
| Integration | Required by multi_grn_scenicplus | Standalone |

Both tools remain in the system — this one is SCENIC+-specific; do not overwrite the other's output.

## Gene annotation

By default, fetched from biomart (`annotation_source='biomart'`). For offline use:
- Set `annotation_source='gtf'` and provide `gtf_path`
- Provide `chromsizes_path` pointing to a UCSC .chrom.sizes file

## Pseudoreplication warning

Fewer than 200 cells raises a warning. For multi-donor datasets with < 5 cells per donor, pseudobulk aggregation before correlation is strongly recommended to avoid inflated significance.

## Outputs stored in adata

| Key | Type | Description |
|-----|------|-------------|
| `adata.uns["scenicplus_peak_gene_links"]` | DataFrame | Filtered links: `[region, target, importance, rho, Distance]` |

**Params:**
- `rna_h5ad_path`: path to paired RNA AnnData (required)
- `species`: organism for biomart TSS annotation and chromosome size fetch (default `'homo_sapiens'`); valid values: `'homo_sapiens'`, `'mus_musculus'`, `'drosophila_melanogaster'`, `'gallus_gallus'`. **Must be set correctly for non-human data** — wrong species silently uses incorrect TSS coordinates, producing near-zero peak-gene links.
- `search_space_upstream/downstream`: `(min_bp, max_bp)` tuples — default `(1000, 150000)` means include peaks 1kb–150kb from TSS
- `search_space_extend_tss`: `(upstream_ext, downstream_ext)` TSS extension in bp (default `(10, 10)`)
- `importance_threshold`: post-hoc RF importance filter (default 0.05); not a parameter of the scoring function
- `rho_threshold`: post-hoc |rho| filter; links with rho > 0 are activating, rho < 0 repressing (default 0.03)
- `importance_scoring_method`: `'GBM'` (gradient boosted, default), `'RF'` (random forest), or `'ET'` (extra trees)
- `n_cpu`: number of parallel workers for importance scoring (default 4)
- `chromsizes_path`: path to a UCSC `.chrom.sizes` file — offline alternative to biomart for chromosome sizes; use with `annotation_source='gtf'` for fully offline runs
- `gtf_path`: path to GTF file for offline gene annotation (used when `annotation_source='gtf'`)

Package: [[packages/scenicplus]]
Method: [[methods/enhancer_grn]]
