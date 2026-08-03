---
type: tool
id: rna_cluster_leiden
stage: cluster
modality: rna
backend: backend/tools/rna/cluster/leiden.py
---

Clusters cells using the Leiden community detection algorithm on a k-nearest neighbor graph.

Key parameters:
- `embedding_key` (required)
- `resolution` (default 1.0)
- `n_neighbors` (default 15)
- `label_key` (default None)

Computes KNN graph (`sc.pp.neighbors()`), then runs Leiden (`sc.tl.leiden()`). Stores cluster labels as string integers ("0", "1", "2", ...).

Metrics stored in `adata.uns["leiden_clusters_metrics"]`: `n_clusters`, and optionally `ari`, `nmi` (if `label_key` provided).

Package: [[packages/leidenalg]], [[packages/scanpy]]
Method: [[methods/graph_based_clustering]]
