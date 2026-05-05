---
type: tool
id: rna_qc_basic
stage: qc
modality: rna
backend: backend/tools/rna/qc/basic.py
---

Filters cells and genes using QC metric thresholds. Computes per-cell metrics (total counts, n_genes, mitochondrial fraction), then removes cells and genes outside acceptable ranges.

Key parameters:
- `min_genes` (default 200): minimum genes detected per cell
- `max_genes` (default None): upper bound; set to remove doublets (e.g., 5000 for PBMCs)
- `min_cells` (default 3): minimum cells a gene must appear in
- `max_mito_frac` (default 0.20): maximum mitochondrial gene fraction; reduce to 0.05 for clean datasets
- `mito_prefix` (default "MT-"): prefix for mitochondrial genes; use "mt-" for mouse

Stores QC metrics in `adata.obs["n_genes_by_counts"]`, `adata.obs["total_counts"]`, `adata.obs["pct_counts_mt"]`. Returns filtered adata.

Package: [[packages/scanpy]]
Method: [[methods/basic_filter]]
