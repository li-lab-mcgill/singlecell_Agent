---
type: tool
id: atac_da_wilcoxon
stage: da
modality: atac
backend: backend/tools/atac/da/wilcoxon.py
---

Performs differential accessibility testing using the Wilcoxon rank-sum test on the peak count matrix.

Key parameters:
- `groupby` (required): `adata.obs` column defining groups (cluster labels or condition)
- `groups` (default "all"): groups to test; "all" = each vs. rest
- `reference` (default "rest"): comparison group
- `n_peaks` (default 500): number of top DA peaks to store per group
- `layer` (default "counts"): peak count layer (raw counts preferred; TF-IDF values also work but LFC interpretation changes)

Output stored in `adata.uns["rank_da_peaks"]`.

Same statistical caveats as RNA Wilcoxon: not valid for multi-donor studies. For multi-donor ATAC DA, use pseudobulk with DESeq2.

Package: [[packages/scanpy]]
Method: [[methods/statistical_da]]
