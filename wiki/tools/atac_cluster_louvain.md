---
type: tool
id: atac_cluster_louvain
stage: cluster
modality: atac
backend: backend/tools/atac/cluster/louvain.py
---

Clusters ATAC cells using Louvain community detection. Legacy method — use `atac_cluster_leiden` for new analyses.

Key parameters: same as `atac_cluster_leiden`.

Use only when reproducing older analyses.

Package: [[packages/scanpy]]
Method: [[methods/graph_based_clustering]]
