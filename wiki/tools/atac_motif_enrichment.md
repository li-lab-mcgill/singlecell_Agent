---
type: tool
id: atac_motif_enrichment
stage: motif
modality: atac
backend: backend/tools/atac/motif/enrichment.py
---

Tests TF motif enrichment in a set of differentially accessible peaks versus a background peak set.

Key parameters:
- `da_peaks` (required): list or array of peak IDs to test (foreground)
- `background_peaks` (default None): background peak set; if None, uses all non-DA peaks; GC-content-matched background is recommended
- `motif_database` (default "JASPAR2024"): motif database to use; "JASPAR2024" or "HOCOMOCO_v12"
- `genome` (default "hg38"): genome for sequence extraction
- `fdr_threshold` (default 0.05): adjusted p-value threshold
- `n_background` (default 3000): number of GC-matched background peaks to use if background_peaks is None

Uses Fisher's exact test for each motif: 2×2 contingency table of (foreground/background) × (motif present/absent).

Output: `adata.uns["motif_enrichment"]` — DataFrame with motif name, odds ratio, pvalue, padj, matching_tf (TF associated with the motif).

Package: [[packages/snapatac2]]
Method: [[methods/motif_enrichment]]
