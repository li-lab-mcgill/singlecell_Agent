---
type: tool
id: atac_cluster_leiden
stage: cluster
modality: atac
backend: backend/tools/atac/cluster/leiden.py
---

Clusters ATAC cells using Leiden community detection. Same algorithm as `rna_cluster_leiden` but operates on the spectral embedding.

Key parameters:
- `embedding_key` (required): e.g., `"X_spectral_harmony"` (batch-corrected) or `"X_spectral"` (no correction)
- `resolution` (default 1.0): cluster granularity
- `n_neighbors` (default 15): KNN neighbors
- `cluster_key` (default "atac_leiden_clusters"): output `adata.obs` column
- `label_key` (default None): optional ground-truth label for ARI/NMI computation

Note: always use the spectral embedding that excludes component 1 (depth component). If `embedding_key="X_spectral"`, the tool internally skips component 0.

Package: [[packages/leidenalg]], [[packages/snapatac2]]
Method: [[methods/graph_based_clustering]]
