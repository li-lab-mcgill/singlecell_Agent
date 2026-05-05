---
type: tool
id: atac_project_umap
stage: project
modality: atac
backend: backend/tools/atac/project/umap.py
---

Computes UMAP 2D layout for ATAC data from the spectral embedding or existing neighbor graph.

Key parameters:
- `embedding_key` (default None): if provided, recomputes KNN graph from this embedding; if None, uses existing `adata.obsp["connectivities"]`
- `n_neighbors` (default 15): KNN neighbors; only used if `embedding_key` is provided
- `min_dist` (default 0.5): UMAP cluster separation; lower = more separated
- `n_components` (default 2): dimensions of UMAP output

Stores result in `adata.obsm["X_umap"]`.

Same UMAP algorithm as `rna_project_umap`. The spectral embedding produces well-structured UMAP layouts when the first (depth-correlated) spectral component is excluded before neighbor computation.

Package: [[packages/scanpy]]
Method: [[methods/nonlinear_projection]]
