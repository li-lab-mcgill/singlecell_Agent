---
type: task
id: atac_differential_accessibility
modality: atac
label: ATAC Differential Accessibility
eval_weights:
  fdr_calibration: 0.4
  lfc_accuracy: 0.3
  ranking_auprc: 0.3
---
Identifies genomic regions that are differentially accessible between cell types or conditions. Produces a ranked list of peaks with fold changes and statistical significance.

DA peaks are the ATAC analog of DE genes. They are used downstream for motif enrichment analysis to identify TF regulators.

Stages (in order):
- [[stages/qc]] [includes]
- [[stages/peak_calling]] [includes]
- [[stages/feature_selection]] [includes]
- [[stages/embed]] [includes]
- [[stages/cluster]] [includes]
- [[stages/da]] [includes]

Evaluated by:
- [[tools/eval_da_metrics]] [evaluated_by]

Key decisions for the consultant:
- **Pseudobulk** (default when `donor_key` present and ≥3 donors per group): statistically valid; uses PyDESeq2 on raw peak counts
- **Wilcoxon** (default for single-sample or exploratory): fast; inflate FDR in multi-donor studies
- Raw integer peak counts required for pseudobulk — not TF-IDF normalized values
- Contrast must specify the comparison: between two cell types, or between conditions within one cell type
