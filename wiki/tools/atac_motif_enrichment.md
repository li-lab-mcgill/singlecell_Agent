---
type: tool
id: atac_motif_enrichment
stage: motif
modality: atac
backend: backend/tools/atac/motif/enrichment.py
---

Tests TF motif enrichment in a set of differentially accessible peaks versus a background peak set.

Key parameters:
- `group_key` (required)
- `genome_fasta_path` (required)
- `motif_db` (default "JASPAR2024")
- `organism` (default "human")
- `test_method` (default "hypergeometric")

Uses Fisher's exact test for each motif: 2×2 contingency table of (foreground/background) × (motif present/absent).

Output: `adata.uns["motif_enrichment"]` — DataFrame with motif name, odds ratio, pvalue, padj, matching_tf (TF associated with the motif).

Package: [[packages/snapatac2]]
Method: [[methods/motif_enrichment]]
