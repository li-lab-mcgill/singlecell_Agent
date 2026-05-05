---
type: method
id: nonlinear_projection
label: Nonlinear Dimensionality Projection (UMAP/t-SNE)
---

Nonlinear projection creates a 2D layout of cells for visualization. It preserves local neighborhood structure from the high-dimensional embedding but is not suitable as input for clustering or quantitative analysis.

**UMAP** (Uniform Manifold Approximation and Projection) is the standard. It runs on the KNN graph from `sc.pp.neighbors()` (or the BBKNN-corrected graph). Key parameters:
- `min_dist` (default 0.5): controls how tightly cells are packed; lower = more cluster separation
- `spread` (default 1.0): controls overall scale; usually left at default

**t-SNE** is an older alternative. It is slower than UMAP, does not preserve global structure (distances between clusters are not meaningful), and is generally not recommended for new analyses. Use only when reproducing older results.

UMAP coordinates are stored in `adata.obsm["X_umap"]`. These coordinates change with random seed — do not compare UMAP coordinates across runs. Only cluster membership and embedding distances are reproducible.

Always compute UMAP after clustering, using the same graph. Do not recompute `sc.pp.neighbors()` between clustering and UMAP — they must use the same graph.

Edges:
- [[tools/rna_project_umap]] implements
- [[tools/atac_project_umap]] implements
