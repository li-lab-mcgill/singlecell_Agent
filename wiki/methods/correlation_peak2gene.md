---
type: method
id: correlation_peak2gene
label: Correlation-based Peak-to-Gene Linkage
---

Correlation-based peak-to-gene linkage computes statistical correlations between peak accessibility and gene expression across cells (for paired data) or across pseudocells. Peaks with significant positive correlation to a gene are linked as putative cis-regulatory elements.

Requires paired RNA+ATAC measurements per cell (10x Multiome, SHARE-seq) or highly matched unpaired datasets aligned in a joint embedding.

Workflow:
1. For each gene, identify candidate peaks within a window (typically ±500 kb of TSS)
2. Compute Pearson or Spearman correlation between peak accessibility and gene expression across cells
3. Permutation test or analytical correction for multiple testing
4. Filter by correlation threshold (r > 0.2) and FDR (< 0.05)

The backend implements this directly with scipy correlations for portability.

Key parameters:
- `peak_gene_correlation_threshold`: minimum correlation to report a link (default 0.2)
- `peak_gene_distance`: search window around TSS (default 500 kb)

Output stored in `adata.uns["peak_gene_links"]` as a list of records with peak, gene, correlation, and distance.

Edges:
- [[tools/atac_peak_to_gene_correlation]] implements
