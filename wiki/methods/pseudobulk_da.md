---
type: method
id: pseudobulk_da
label: Pseudobulk Differential Accessibility
---

Pseudobulk DA aggregates peak counts per donor×cell-type and applies bulk DE tools (DESeq2 or edgeR) to find differentially accessible peaks. Same statistical rationale as pseudobulk DE.

Workflow:
1. Subset to cell type of interest
2. Sum peak counts per donor → (donors × peaks) matrix
3. Run DESeq2 with condition as the design factor

Requirements: raw integer peak counts (not TF-IDF normalized), ≥3 donors per group, donor/sample column in `adata.obs`.

DESeq2 on ATAC pseudobulk has been validated in multiple benchmarking studies as providing well-calibrated FDR for multi-sample differential accessibility.

Output: peak-level DataFrame with `log2FoldChange`, `pvalue`, `padj`, `baseMean`.

Edges:
No executable backend tool currently implements ATAC pseudobulk DA.
