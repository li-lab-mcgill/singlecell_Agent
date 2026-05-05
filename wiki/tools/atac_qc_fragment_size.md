---
type: tool
id: atac_qc_fragment_size
stage: qc
modality: atac
backend: backend/tools/atac/qc/fragment_size.py
---

Computes and plots the fragment size distribution for ATAC QC. A high-quality ATAC library should show a clear nucleosome banding pattern: enrichment at <200 bp (nucleosome-free), a trough, then lower peaks at ~200 bp (mono-nucleosome), ~400 bp (di-nucleosome), etc.

This tool is diagnostic — it does not filter cells. Use it to assess library quality before proceeding with `atac_qc_basic`.

Key parameters:
- `max_fragment_length` (default 800): maximum fragment length to plot
- `n_cells` (default 1000): number of cells to sample for the distribution plot (full dataset can be slow)

Output: `adata.uns["fragment_size_distribution"]` with per-length counts; also generates a plot if `plot=True`.

A library without clear nucleosome banding (flat distribution) indicates Tn5 digestion or library preparation failure and should be excluded.

Package: [[packages/snapatac2]]
Method: [[methods/basic_filter]]
