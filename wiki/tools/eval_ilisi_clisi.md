---
type: tool
id: eval_ilisi_clisi
stage: eval
modality: rna, atac, multi
backend: backend/tools/eval/ilisi_clisi.py
---

Computes iLISI (integration LISI) and cLISI (cell type LISI) using scib-metrics. Both metrics use the local inverse Simpson's index on the KNN graph to measure neighborhood diversity.

Key parameters:
- `embedding_key` (required)
- `batch_key` (required)
- `label_key` (default None)

Returns:
- `ilisi`: mean iLISI across all cells; range [1, n_batches]; higher = better batch mixing
- `clisi`: mean cLISI across all cells; range [1, n_cell_types]; higher = better cell type purity

Stores in `adata.uns["lisi_metrics"]`.

Package: [[packages/scib_metrics]]
Method: [[methods/batch_metrics]]
