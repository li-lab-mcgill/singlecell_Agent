---
type: tool
id: atac_cluster_leiden
stage: cluster
modality: atac
backend: backend/tools/atac/cluster/leiden.py
---

Clusters ATAC cells using Leiden community detection. Same algorithm as `rna_cluster_leiden` but operates on the spectral embedding.

Key parameters:
- `embedding_key` (default "X_lsi")
- `resolution` (default 1.0)
- `n_neighbors` (default 15)
- `label_key` (default None)

Note: always use the spectral embedding that excludes component 1 (depth component). If `embedding_key="X_spectral"`, the tool internally skips component 0.

Package: [[packages/leidenalg]], [[packages/snapatac2]]
Method: [[methods/graph_based_clustering]]
