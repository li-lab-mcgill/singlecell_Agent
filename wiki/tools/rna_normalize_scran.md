---
type: tool
id: rna_normalize_scran
stage: normalize
modality: rna
backend: backend/tools/rna/normalize/scran.py
---

Normalizes using scran's pooling-based size factor estimation. More accurate than simple library size normalization for datasets with compositional differences between cell types.

scran pools cells of similar expression profiles, computes pool-based size factors, then deconvolves to per-cell size factors. This handles the problem that some genes are highly expressed in one cell type and low in another, which biases simple total-count normalization.

Key parameters:
- `min_cluster_size` (default 100): minimum cells per cluster for pool-based estimation; reduce for small datasets
- `log_transform` (default True): apply log1p after size factor normalization

Requires R and the `rpy2` Python-R bridge. Falls back to `rna_normalize_log1p` if R is not available.

Use when: dataset has strong compositional differences between cell types, or when reproducing analyses that specified scran normalization.

Package: [[packages/scanpy]] (via rpy2/R scran package)
Method: [[methods/library_size_normalization]]
