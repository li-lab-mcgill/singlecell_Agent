---
type: tool
id: atac_da_wilcoxon
stage: da
modality: atac
backend: backend/tools/atac/da/wilcoxon.py
---

Performs differential accessibility testing using the Wilcoxon rank-sum test on the peak count matrix.

Key parameters:
- `group_key` (required)
- `reference` (default "rest")
- `top_n` (default 50)

Output stored in `adata.uns["rank_peaks_groups"]`.

Same statistical caveats as RNA Wilcoxon: not valid for multi-donor studies. For multi-donor ATAC DA, use pseudobulk with DESeq2.

Package: [[packages/scanpy]]
Method: [[methods/statistical_da]]
