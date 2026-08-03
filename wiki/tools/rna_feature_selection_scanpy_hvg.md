---
type: tool
id: rna_feature_selection_scanpy_hvg
stage: feature_selection
modality: rna
backend: backend/tools/rna/feature_selection/scanpy_hvg.py
---

Selects highly variable genes using scanpy's `sc.pp.highly_variable_genes()`. Fits a mean-dispersion trend and marks genes above the trend as highly variable.

Key parameters:
- `n_top` (default 2000)
- `batch_key` (default None)

Stores `adata.var["highly_variable"]` bool column. Downstream PCA uses only HVGs.

Package: [[packages/scanpy]]
Method: [[methods/highly_variable_genes]]
