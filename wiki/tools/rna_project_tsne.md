---
type: tool
id: rna_project_tsne
stage: project
modality: rna
backend: backend/tools/rna/project/tsne.py
---

Computes t-SNE 2D coordinates for visualization.

Key parameters:
- `embedding_key` (default "X_pca"): embedding to use as input; t-SNE runs on the embedding, not the raw expression
- `perplexity` (default 30): controls neighborhood size; typically 5–50; reduce for small datasets
- `n_pcs` (default 30): number of PCA components to use

Stores result in `adata.obsm["X_tsne"]`.

t-SNE does not preserve global structure — distances between clusters in t-SNE space are not meaningful. Use UMAP for new analyses. Use t-SNE only when reproducing older analyses or when a user specifically requests it.

Package: [[packages/scanpy]]
Method: [[methods/nonlinear_projection]]
