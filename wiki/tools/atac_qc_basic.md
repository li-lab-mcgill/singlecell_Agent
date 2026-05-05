---
type: tool
id: atac_qc_basic
stage: qc
modality: atac
backend: backend/tools/atac/qc/basic.py
---

Filters ATAC cells using standard QC metrics: total fragments, TSS enrichment score, and nucleosome signal.

Key parameters:
- `min_fragments` (default 1000): minimum total fragment count per cell
- `max_fragments` (default None): upper bound; high fragment count may indicate doublets
- `min_tss_score` (default 4.0): minimum TSS enrichment score; cells below this threshold have poor signal quality
- `max_nucleosome_signal` (default 4.0): maximum nucleosome signal (fragments >200 bp / fragments <147 bp); high values indicate poor nucleosome-free enrichment

Computes QC metrics using SnapATAC2 if available (`snap.metrics.tsse()`), otherwise uses fragment length distributions from the fragment file.

Stores QC metrics in `adata.obs["n_fragment"]`, `adata.obs["tsse"]`, `adata.obs["nucleosome_signal"]`.

Package: [[packages/snapatac2]]
Method: [[methods/basic_filter]]
