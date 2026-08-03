---
type: tool
id: rna_batch_integration_bbknn
stage: batch_integration
modality: rna
backend: backend/tools/rna/batch_integration/bbknn.py
---

Corrects batch effects by building a batch-balanced k-nearest neighbor graph. Modifies `adata.obsp["connectivities"]` and `adata.obsp["distances"]` in place.

Key parameters:
- `batch_key` (required)
- `embedding_key` (default "X_pca")
- `neighbors_within_batch` (default 3)
- `n_pcs` (default 50)

After BBKNN, run `sc.tl.leiden()` and `sc.tl.umap()` directly — do not re-run `sc.pp.neighbors()` as this would overwrite the BBKNN-corrected graph.

The PCA embedding is NOT modified. Only the neighbor graph changes.

Package: [[packages/bbknn]]
Method: [[methods/graph_correction]]
