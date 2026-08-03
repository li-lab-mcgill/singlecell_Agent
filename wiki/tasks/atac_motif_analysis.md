---
type: task
id: atac_motif_analysis
modality: atac
label: ATAC TF Motif Analysis
eval_weights:
  motif_enrichment_auprc: 0.5
  tf_activity_correlation: 0.5
---
Identifies transcription factor binding motifs enriched in accessible peaks and estimates TF activity across cell types. Connects chromatin accessibility to TF regulatory activity.

Two sub-analyses:
1. **Motif enrichment in DA peaks**: given differential peaks, which TFs are implicated?
2. **Motif scanning for TF activity**: scan all peaks for all motifs → per-cell TF activity matrix

Stages (in order):
- [[stages/qc]] [includes]
- [[stages/peak_calling]] [includes]
- [[stages/feature_selection]] [includes]
- [[stages/embed]] [includes]
- [[stages/cluster]] [includes]
- [[stages/motif]] [includes]

Evaluated by:
No dedicated executable motif evaluation tool is currently registered.

Key decisions for the consultant:
- Motif enrichment requires DA peaks as input → DA analysis must precede motif analysis
- Motif database: JASPAR2024 (open-access, well-maintained); HOCOMOCO for higher sensitivity
- For TF activity scanning: SnapATAC2 `snap.tl.motif_scanning()` is the most efficient implementation
- GC-content-matched background peaks are essential to avoid false enrichment in GC-rich regions
