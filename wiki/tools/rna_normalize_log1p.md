---
type: tool
id: rna_normalize_log1p
stage: normalize
modality: rna
backend: backend/tools/rna/normalize/log1p.py
---

Normalizes each cell to a target sum then applies log1p transformation. The standard normalization step for most scRNA-seq pipelines.

Key parameters:
- `target_sum` (default 10000): counts per cell after normalization (CPM × target_sum/1e6)
- `layer` (default None): if specified, reads from `adata.layers[layer]`; if None, reads from `adata.X`
- `save_raw` (default True): if True, stores original counts in `adata.layers["counts"]` before modifying `adata.X`

Workflow: `sc.pp.normalize_total(target_sum=target_sum)` → `sc.pp.log1p()`.

The `save_raw=True` default is important — raw counts must be preserved for count-based models (scVI, DESeq2 pseudobulk). Do not disable this.

Package: [[packages/scanpy]]
Method: [[methods/library_size_normalization]]
