---
type: tool
id: rna_batch_integration_bbknn
stage: batch_integration
modality: rna
backend: backend/tools/rna/batch_integration/bbknn.py
---

Corrects batch effects by building a batch-balanced k-nearest neighbor graph. Modifies `adata.obsp["connectivities"]` and `adata.obsp["distances"]` in place.

Key parameters:
- `batch_key` (required): `adata.obs` column identifying the batch
- `neighbors_within_batch` (default 3): number of neighbors to find from each batch; increase for datasets with many batches (e.g., >5 batches: use 5–10)
- `n_pcs` (default 50): number of PCA components used for distance computation
- `embedding_key` (default "X_pca"): embedding to use for KNN computation

After BBKNN, run `sc.tl.leiden()` and `sc.tl.umap()` directly — do not re-run `sc.pp.neighbors()` as this would overwrite the BBKNN-corrected graph.

The PCA embedding is NOT modified. Only the neighbor graph changes.

Package: [[packages/bbknn]]
Method: [[methods/graph_correction]]
