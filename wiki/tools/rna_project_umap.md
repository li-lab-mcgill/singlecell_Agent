---
type: tool
id: rna_project_umap
stage: project
modality: rna
backend: backend/tools/rna/project/umap.py
---

Computes UMAP 2D coordinates from the embedding or existing neighbor graph.

Key parameters:
- `embedding_key` (default None): if provided, recomputes the KNN graph using this embedding before UMAP; if None, uses existing `adata.obsp["connectivities"]`
- `n_neighbors` (default 15): KNN neighbors; only used if `embedding_key` is provided
- `min_dist` (default 0.5): controls cluster tightness in UMAP layout; lower = more separated clusters
- `spread` (default 1.0): global scale of the UMAP; usually left at default
- `n_components` (default 2): 2D for visualization; 3D possible but rarely used

Stores result in `adata.obsm["X_umap"]`.

Important: if BBKNN was used for batch correction, call with `embedding_key=None` to use the BBKNN graph. Do not recompute neighbors after BBKNN.

Package: [[packages/scanpy]]
Method: [[methods/nonlinear_projection]]
