---
type: task
id: atac_peak_to_gene
modality: atac
label: ATAC Peak-to-Gene Linkage
eval_weights:
  linkage_precision: 0.5
  linkage_recall: 0.5
---
Links distal regulatory elements (peaks) to their putative target genes. Establishes cis-regulatory relationships between accessible regions and gene expression.

This task ideally requires paired RNA+ATAC data for correlation-based linking. For ATAC-only datasets, distance-based linking (nearest gene) is the fallback.

Stages (in order):
- [[stages/qc]] [includes]
- [[stages/peak_calling]] [includes]
- [[stages/feature_selection]] [includes]
- [[stages/embed]] [includes]
- [[stages/cluster]] [includes]
- [[stages/peak_to_gene]] [includes]

Evaluated by:
No dedicated executable peak-to-gene evaluation tool is currently registered.

Key decisions for the consultant:
- If paired RNA+ATAC is available: use correlation-based linking (`atac_peak_to_gene_correlation`)
- If ATAC-only: use distance-based linking (nearest gene within 100 kb)
- Distance window: 500 kb is standard; narrow to 100 kb for conservative, high-confidence links
- Output links should be filtered by both correlation threshold AND adjusted p-value
