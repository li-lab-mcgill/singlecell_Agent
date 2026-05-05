---
type: tool
id: rna_normalize_sctransform
stage: normalize
modality: rna
backend: backend/tools/rna/normalize/sctransform.py
---

Normalizes using analytic Pearson residuals (scTransform-style variance stabilization). Models each gene's counts as negative binomial and returns residuals that are variance-stabilized across all expression levels.

Key parameters:
- `n_top_genes` (default 3000): number of highly variable genes to select after computing residuals
- `inplace` (default True): if True, stores results in `adata.X`; raw counts preserved in `adata.layers["counts"]`

Uses `sc.experimental.pp.normalize_pearson_residuals()`. This produces a matrix where variance is decoupled from mean expression, benefiting PCA and other linear methods.

Use this instead of log1p when library sizes vary dramatically between cells or when the user requests Seurat v3-style normalization.

Package: [[packages/scanpy]]
Method: [[methods/variance_stabilization]]
