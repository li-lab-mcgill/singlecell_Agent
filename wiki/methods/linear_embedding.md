---
type: method
id: linear_embedding
label: Linear Embedding (PCA)
---

Principal Component Analysis (PCA) is the standard linear dimensionality reduction for scRNA-seq. It projects the HVG expression matrix onto the axes of maximum variance, producing a low-dimensional embedding where each axis is a linear combination of gene expression.

PCA is fast, interpretable, and a prerequisite for Harmony batch correction. It is not optimal for highly non-linear biological variation or for datasets with very strong batch effects.

Key parameters:
- `n_comps`: number of PCs to compute; typically 30–50; use an elbow plot to find the point of diminishing return
- `use_highly_variable`: must be True; PCA on all genes is noisy and slow
- `zero_center`: True by default; do not change

Output stored in `adata.obsm["X_pca"]` and `adata.varm["PCs"]`.

After PCA, inspect the explained variance ratio to select the number of PCs to carry forward. A scree plot where variance drops sharply then plateaus suggests an appropriate cutoff. For most PBMC datasets, 15–30 PCs are informative.

Edges:
- [[tools/rna_embed_pca]] implements
