---
type: tool
id: rna_embed_seurat_pca
stage: embed
modality: rna
backend: backend/tools/rna/embed/seurat_pca.py
---

Computes PCA using Seurat v3-style preprocessing (SCTransform normalization + PCA). Produces a PCA embedding comparable to Seurat workflows for cross-tool reproducibility.

Key parameters:
- `n_pcs` (default 50)
- `random_seed` (default 42)

This tool applies Pearson residuals normalization internally before PCA, equivalent to Seurat's `SCTransform() → RunPCA()` workflow.

Use when: reproducing a Seurat analysis or comparing results to a published Seurat-based study.

Stores embedding in `adata.obsm["X_seurat_pca"]` by default.

Package: [[packages/scanpy]]
Method: [[methods/linear_embedding]]
