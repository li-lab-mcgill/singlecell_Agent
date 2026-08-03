---
type: tool
id: atac_project_umap
stage: project
modality: atac
backend: backend/tools/atac/project/umap.py
---

Computes UMAP 2D layout for ATAC data from the spectral embedding or existing neighbor graph.

Key parameters:
- `embedding_key` (default "X_lsi")
- `n_neighbors` (default 15)
- `min_dist` (default 0.5)
- `spread` (default 1.0)
- `random_seed` (default 42)

Stores result in `adata.obsm["X_umap"]`.

Same UMAP algorithm as `rna_project_umap`. The spectral embedding produces well-structured UMAP layouts when the first (depth-correlated) spectral component is excluded before neighbor computation.

Package: [[packages/scanpy]]
Method: [[methods/nonlinear_projection]]
