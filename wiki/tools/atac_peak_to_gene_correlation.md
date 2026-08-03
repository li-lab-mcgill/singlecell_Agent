---
type: tool
id: atac_peak_to_gene_correlation
stage: peak_to_gene
modality: atac
backend: backend/tools/atac/peak_to_gene/correlation.py
---

Links ATAC peaks to target genes using correlation between peak accessibility and gene expression across cells. Requires paired RNA+ATAC data (e.g., 10x Multiome) or pseudocell aggregates.

Key parameters:
- `rna_h5ad_path` (default None)
- `max_distance` (default 500000)
- `min_correlation` (default 0.05)
- `gtf_path` (default None)

Output: `adata.uns["peak_gene_links"]` — DataFrame with columns: peak, gene, correlation, pvalue, padj.

For ATAC-only datasets without paired RNA: falls back to distance-based linking (nearest gene within `peak_gene_distance`).

Package: [[packages/snapatac2]]
Method: [[methods/correlation_peak2gene]]
