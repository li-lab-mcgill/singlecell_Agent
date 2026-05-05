---
type: stage
id: cluster
label: Clustering
---

The clustering stage partitions cells into discrete groups based on similarity in the embedding space. Clusters serve as the unit of analysis for annotation, DE, and DA.

Graph-based methods (Leiden, Louvain) first build a k-nearest neighbor graph, then detect communities. They are preferred for single-cell data because they scale well and handle non-convex cluster shapes. The `resolution` parameter is the primary lever for controlling cluster granularity.

Edges:
- [[methods/graph_based_clustering]] modality: rna, atac, multi
