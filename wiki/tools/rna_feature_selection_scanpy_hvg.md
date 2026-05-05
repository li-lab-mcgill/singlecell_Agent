---
type: tool
id: rna_feature_selection_scanpy_hvg
stage: feature_selection
modality: rna
backend: backend/tools/rna/feature_selection/scanpy_hvg.py
---

Selects highly variable genes using scanpy's `sc.pp.highly_variable_genes()`. Fits a mean-dispersion trend and marks genes above the trend as highly variable.

Key parameters:
- `n_top_genes` (default 2000): number of HVGs to select
- `flavor` (default "seurat_v3"): `"seurat_v3"` uses variance on raw counts (recommended); `"cell_ranger"` uses log-normalized dispersion
- `batch_key` (default None): if set, computes HVGs per batch and takes the intersection; recommended for multi-batch datasets
- `min_mean` (default 0.0125), `max_mean` (default 3.0): mean expression range for HVG candidates

Stores `adata.var["highly_variable"]` bool column. Downstream PCA uses only HVGs.

Package: [[packages/scanpy]]
Method: [[methods/highly_variable_genes]]
