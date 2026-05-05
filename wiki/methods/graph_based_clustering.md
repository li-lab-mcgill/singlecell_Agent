---
type: method
id: graph_based_clustering
label: Graph-based Clustering
---

Graph-based clustering builds a shared nearest neighbor (SNN) graph from the low-dimensional embedding, then applies a community detection algorithm to partition cells into clusters.

The pipeline has two steps:
1. `sc.pp.neighbors()` — constructs KNN graph using cosine distance on the embedding; `n_neighbors` controls local neighborhood size (typically 10–30)
2. `sc.tl.leiden()` or `sc.tl.louvain()` — community detection on the SNN graph

**Leiden** is the preferred algorithm. It guarantees well-connected communities and is more reproducible than Louvain. Always use Leiden for new analyses.

**Louvain** is included only for reproducing older published analyses. Its communities can have disconnected subgraphs.

The `resolution` parameter is the primary control for cluster granularity:
- Lower values (0.1–0.5): fewer, larger clusters
- Higher values (0.5–2.0): more, finer-grained clusters
- Typical starting point: 0.5 for broad cell types, 1.0 for subtypes

If BBKNN was used for batch correction, pass `use_rep=None` to `sc.pp.neighbors()` to use the pre-existing BBKNN graph instead of recomputing neighbors.

Edges:
- [[tools/rna_cluster_leiden]] implements
- [[tools/rna_cluster_louvain]] implements
- [[tools/atac_cluster_leiden]] implements
