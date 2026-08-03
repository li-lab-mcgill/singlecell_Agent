---
type: tool
id: rna_embed_pca
stage: embed
modality: rna
backend: backend/tools/rna/embed/pca.py
---

Computes PCA on the HVG expression matrix and stores the embedding in `adata.obsm["X_pca"]`.

Key parameters:
- `n_pcs` (default 50)
- `random_seed` (default 42)

Also stores:
- `adata.varm["PCs"]`: gene loadings per PC
- `adata.uns["pca"]["variance_ratio"]`: explained variance fraction per PC — use to select n_pcs for downstream steps

After PCA, use `sc.pl.pca_variance_ratio()` to visualize the elbow. For most PBMC datasets, PCs 1–30 capture the meaningful variation.

Package: [[packages/scanpy]]
Method: [[methods/linear_embedding]]
