---
type: tool
id: rna_cluster_louvain
stage: cluster
modality: rna
backend: backend/tools/rna/cluster/louvain.py
---

Clusters cells using the Louvain community detection algorithm. Legacy method — use Leiden for new analyses.

Key parameters:
- `embedding_key` (required): embedding for KNN graph
- `resolution` (default 1.0): cluster granularity
- `n_neighbors` (default 15): KNN neighbors
- `cluster_key` (default "louvain_clusters"): `adata.obs` output column

Louvain can produce disconnected communities. Use only when reproducing analyses that specified Louvain, or when comparing directly against a published Louvain-based study.

Package: [[packages/scanpy]]
Method: [[methods/graph_based_clustering]]
