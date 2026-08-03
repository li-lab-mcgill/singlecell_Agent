---
type: tool
id: rna_project_tsne
stage: project
modality: rna
backend: backend/tools/rna/project/tsne.py
---

Computes t-SNE 2D coordinates for visualization.

Key parameters:
- `embedding_key` (required)
- `n_neighbors` (default 15)
- `perplexity` (default 30.0)
- `random_seed` (default 42)

Stores result in `adata.obsm["X_tsne"]`.

t-SNE does not preserve global structure — distances between clusters in t-SNE space are not meaningful. Use UMAP for new analyses. Use t-SNE only when reproducing older analyses or when a user specifically requests it.

Package: [[packages/scanpy]]
Method: [[methods/nonlinear_projection]]
