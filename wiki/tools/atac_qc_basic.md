---
type: tool
id: atac_qc_basic
stage: qc
modality: atac
backend: backend/tools/atac/qc/basic.py
---

Filters ATAC cells using standard QC metrics: total fragments, TSS enrichment score, and nucleosome signal.

Key parameters:
- `build` (default "hg38")
- `min_counts` (default 1000)
- `max_counts` (default 50000)
- `min_features` (default 500)
- `min_cells` (default 10)

Computes QC metrics using SnapATAC2 if available (`snap.metrics.tsse()`), otherwise uses fragment length distributions from the fragment file.

Stores QC metrics in `adata.obs["n_fragment"]`, `adata.obs["tsse"]`, `adata.obs["nucleosome_signal"]`.

Package: [[packages/snapatac2]]
Method: [[methods/basic_filter]]
