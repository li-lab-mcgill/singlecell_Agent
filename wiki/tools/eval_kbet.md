---
type: tool
id: eval_kbet
stage: eval
modality: rna, atac, multi
backend: backend/tools/eval/kbet.py
---

Computes kBET (k-nearest neighbor Batch Effect Test) acceptance rate to quantify batch mixing.

Key parameters:
- `embedding_key` (required)
- `batch_key` (required)
- `subsample` (default 5000)

kBET tests whether the batch label distribution in each cell's k-neighborhood matches the global distribution. The acceptance rate (fraction of cells passing the test) is the metric: higher = better batch mixing.

Returns `kbet_acceptance_rate` (range 0–1) stored in `adata.uns["kbet"]`.

Package: [[packages/scib_metrics]]
Method: [[methods/batch_metrics]]
