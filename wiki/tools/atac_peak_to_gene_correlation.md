---
type: tool
id: atac_peak_to_gene_correlation
stage: peak_to_gene
modality: atac
backend: backend/tools/atac/peak_to_gene/correlation.py
---

Links ATAC peaks to target genes using correlation between peak accessibility and gene expression across cells. Requires paired RNA+ATAC data (e.g., 10x Multiome) or pseudocell aggregates.

Key parameters:
- `rna_adata` (required): RNA AnnData with expression values; cells must be aligned to ATAC adata
- `peak_gene_distance` (default 500000): search window around TSS in bp
- `correlation_method` (default "pearson"): "pearson" or "spearman"
- `min_correlation` (default 0.2): minimum correlation to report a link
- `fdr_threshold` (default 0.05): adjusted p-value threshold
- `n_cells_per_pseudocell` (default None): if set, aggregates cells into pseudocells before computing correlations (reduces noise)

Output: `adata.uns["peak_gene_links"]` — DataFrame with columns: peak, gene, correlation, pvalue, padj.

For ATAC-only datasets without paired RNA: falls back to distance-based linking (nearest gene within `peak_gene_distance`).

Package: [[packages/snapatac2]]
Method: [[methods/correlation_peak2gene]]
