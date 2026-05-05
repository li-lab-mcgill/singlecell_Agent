---
type: tool
id: rna_embed_pca
stage: embed
modality: rna
backend: backend/tools/rna/embed/pca.py
---

Computes PCA on the HVG expression matrix and stores the embedding in `adata.obsm["X_pca"]`.

Key parameters:
- `n_comps` (default 50): number of principal components; use scree plot to select informative PCs for downstream analysis
- `use_highly_variable` (default True): subset to HVG genes before PCA
- `svd_solver` (default "arpack"): use "randomized" for very large datasets (>100k cells) for speed

Also stores:
- `adata.varm["PCs"]`: gene loadings per PC
- `adata.uns["pca"]["variance_ratio"]`: explained variance fraction per PC — use to select n_pcs for downstream steps

After PCA, use `sc.pl.pca_variance_ratio()` to visualize the elbow. For most PBMC datasets, PCs 1–30 capture the meaningful variation.

Package: [[packages/scanpy]]
Method: [[methods/linear_embedding]]
