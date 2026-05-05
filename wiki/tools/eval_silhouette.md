---
type: tool
id: eval_silhouette
stage: eval
modality: rna, atac, multi
backend: backend/tools/eval/silhouette.py
---

Computes the silhouette score for clustering quality assessment. Does not require ground-truth labels.

Key parameters:
- `cluster_key` (required): `adata.obs` column with cluster labels
- `embedding_key` (required): `adata.obsm` key for the embedding used to compute cell-cell distances; e.g., `"X_pca"` or `"X_harmony"`
- `sample_n` (default 10000): number of cells to sample for silhouette computation; silhouette scales as O(n²), so sampling is used for large datasets
- `metric` (default "euclidean"): distance metric

Returns silhouette coefficient per cell (range -1 to 1) and the global mean. Stores in `adata.uns["silhouette"]`.

Always compute silhouette on the embedding (PCA or corrected), NOT on UMAP coordinates. UMAP coordinates are non-linearly distorted and silhouette scores computed on them are not meaningful.

Package: [[packages/sklearn]]
Method: [[methods/clustering_metrics]]
