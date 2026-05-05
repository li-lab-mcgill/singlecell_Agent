---
type: tool
id: rna_cluster_leiden
stage: cluster
modality: rna
backend: backend/tools/rna/cluster/leiden.py
---

Clusters cells using the Leiden community detection algorithm on a k-nearest neighbor graph.

Key parameters:
- `embedding_key` (required): which embedding to use for KNN graph construction (e.g., `"X_pca"`, `"X_harmony"`, `"X_scvi"`)
- `resolution` (default 1.0): cluster granularity; 0.5 for broad types, 1.0–2.0 for subtypes
- `n_neighbors` (default 15): number of neighbors for KNN graph; increase for larger datasets
- `cluster_key` (default "leiden_clusters"): `adata.obs` column name for cluster labels
- `label_key` (default None): if provided, computes ARI and NMI against this ground-truth label column

Computes KNN graph (`sc.pp.neighbors()`), then runs Leiden (`sc.tl.leiden()`). Stores cluster labels as string integers ("0", "1", "2", ...).

Metrics stored in `adata.uns["leiden_clusters_metrics"]`: `n_clusters`, and optionally `ari`, `nmi` (if `label_key` provided).

Package: [[packages/leidenalg]], [[packages/scanpy]]
Method: [[methods/graph_based_clustering]]
