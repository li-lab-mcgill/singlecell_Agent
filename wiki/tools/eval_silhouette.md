---
type: tool
id: eval_silhouette
stage: eval
modality: rna, atac, multi
backend: backend/tools/eval/silhouette.py
---

Computes the silhouette score for clustering quality assessment. Does not require ground-truth labels.

Key parameters:
- `cluster_key` (required)
- `embedding_key` (required)
- `subsample` (default 10000)

Returns silhouette coefficient per cell (range -1 to 1) and the global mean. Stores in `adata.uns["silhouette"]`.

Always compute silhouette on the embedding (PCA or corrected), NOT on UMAP coordinates. UMAP coordinates are non-linearly distorted and silhouette scores computed on them are not meaningful.

Package: [[packages/sklearn]]
Method: [[methods/clustering_metrics]]
