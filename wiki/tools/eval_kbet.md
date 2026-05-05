---
type: tool
id: eval_kbet
stage: eval
modality: rna, atac, multi
backend: backend/tools/eval/kbet.py
---

Computes kBET (k-nearest neighbor Batch Effect Test) acceptance rate to quantify batch mixing.

Key parameters:
- `batch_key` (required): `adata.obs` column for batch labels
- `embedding_key` (required): `adata.obsm` key for the integrated embedding to evaluate
- `k0` (default None): number of neighbors for each cell's test; if None, auto-set to `sqrt(n_cells)`
- `testsize` (default 0.1): fraction of cells to test (random subsample); kBET is slow on full datasets
- `alpha` (default 0.05): significance level for the chi-square test

kBET tests whether the batch label distribution in each cell's k-neighborhood matches the global distribution. The acceptance rate (fraction of cells passing the test) is the metric: higher = better batch mixing.

Returns `kbet_acceptance_rate` (range 0–1) stored in `adata.uns["kbet"]`.

Package: [[packages/scib_metrics]]
Method: [[methods/batch_metrics]]
