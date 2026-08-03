---
type: tool
id: rna_normalize_log1p
stage: normalize
modality: rna
backend: backend/tools/rna/normalize/log1p.py
---

Normalizes each cell to a target sum then applies log1p transformation. The standard normalization step for most scRNA-seq pipelines.

Key parameters:
- `target_sum` (default 10000.0)

Raw counts are always saved to `adata.layers["counts"]` before normalization — required for downstream count-based models (scVI, DESeq2 pseudobulk).

Workflow: `sc.pp.normalize_total(target_sum=target_sum)` → `sc.pp.log1p()`.

Package: [[packages/scanpy]]
Method: [[methods/library_size_normalization]]
