---
type: method
id: pseudobulk_de
label: Pseudobulk Differential Expression
---

Pseudobulk DE aggregates raw counts per donor×cell-type combination to create pseudo-samples, then applies bulk RNA-seq DE methods. This properly accounts for the correlation structure of cells from the same donor.

Workflow:
1. Subset `adata` to the cell type of interest
2. Sum raw counts across all cells per donor → creates a (donors × genes) count matrix
3. Run DESeq2 (via PyDESeq2) or edgeR on the pseudo-sample matrix with a design formula for condition

This approach has the correct null distribution and type I error rate, unlike cell-level tests which are systematically anti-conservative.

Requirements:
- At least 3 donors per group (DESeq2 requires ≥3 for reliable dispersion estimation)
- Raw integer counts in `adata.layers["counts"]` — pseudobulk must use raw counts, not log-normalized values
- A donor/sample column in `adata.obs` (e.g., `"donor_id"` or `"sample"`)

Output: gene-level DataFrame with `log2FoldChange`, `pvalue`, `padj` (BH-corrected), `baseMean`.

Pseudobulk is the gold standard for multi-sample DE. In benchmarks, it consistently outperforms cell-level tests in FDR control and power when donor replicates are available.

Edges:
- [[tools/rna_de_pseudobulk]] implements
