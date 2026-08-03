---
type: tool
id: rna_qc_basic
stage: qc
modality: rna
backend: backend/tools/rna/qc/basic.py
---

Filters cells and genes using QC metric thresholds. Computes per-cell metrics (total counts, n_genes, mitochondrial fraction), then removes cells and genes outside acceptable ranges.

Key parameters:
- `min_genes` (default 200)
- `max_pct_mito` (default 20.0)
- `min_cells` (default 3)
- `mt_pattern` (default "^MT-")

Stores QC metrics in `adata.obs["n_genes_by_counts"]`, `adata.obs["total_counts"]`, `adata.obs["pct_counts_mt"]`. Returns filtered adata.

Package: [[packages/scanpy]]
Method: [[methods/basic_filter]]
