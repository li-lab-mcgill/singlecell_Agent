---
type: stage
id: da
label: Differential Accessibility
---

The DA stage identifies genomic regions (peaks) that are differentially accessible between cell populations or conditions. It is the ATAC analog of differential expression.

DA methods operate on peak count matrices after library size normalization. Unlike DE, peak counts are sparser and more binary, which affects method choice.

Methods:
- **Wilcoxon/logistic regression**: fast cell-level tests; same caveats as RNA DE (donor inflation)
- **Pseudobulk + DESeq2/edgeR**: donor-aware; recommended for multi-sample ATAC
- **SnapATAC2 diff_test**: logistic regression on pseudo-bulk; efficient for large datasets

Output: peak × condition table with log fold change, p-value, and FDR-adjusted p-value.

Edges:
- [[methods/statistical_da]] modality: atac, multi
- [[methods/pseudobulk_da]] modality: atac, multi
