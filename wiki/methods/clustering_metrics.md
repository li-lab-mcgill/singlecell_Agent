---
type: method
id: clustering_metrics
label: Clustering Quality Metrics
---

Clustering metrics quantify the quality of cell clusters, measuring both agreement with a reference label (when available) and intrinsic cluster coherence (when no reference is available).

**External metrics** (require ground-truth labels):
- **ARI** (Adjusted Rand Index): measures agreement between predicted clusters and true labels, adjusted for chance; range [-1, 1]; 1 = perfect, 0 = random; insensitive to label permutation
- **NMI** (Normalized Mutual Information): information-theoretic agreement; range [0, 1]; 1 = perfect agreement; symmetric between predicted and true

**Internal metrics** (no labels required):
- **Silhouette score**: measures how similar each cell is to its own cluster vs. neighboring clusters; range [-1, 1]; 1 = tight, well-separated clusters; requires a distance matrix

Computed using sklearn: `adjusted_rand_score`, `normalized_mutual_info_score`, `silhouette_score`.

For silhouette score, pass the embedding (`adata.obsm["X_pca"]`) not UMAP coordinates. Silhouette on UMAP coordinates is biased by the non-linear projection.

Edges:
- [[tools/eval_clustering_metrics]] implements
