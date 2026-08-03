---
type: tool
id: rna_project_umap
stage: project
modality: rna
backend: backend/tools/rna/project/umap.py
---

Computes UMAP 2D coordinates from the embedding or existing neighbor graph.

Key parameters:
- `embedding_key` (required)
- `n_neighbors` (default 15)
- `min_dist` (default 0.5)
- `spread` (default 1.0)
- `random_seed` (default 42)

Stores result in `adata.obsm["X_umap"]`.

Important: `embedding_key` is required and must exist in `adata.obsm`. The tool always recomputes the neighbor graph from this embedding before running UMAP.

Package: [[packages/scanpy]]
Method: [[methods/nonlinear_projection]]
