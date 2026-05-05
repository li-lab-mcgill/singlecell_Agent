---
type: task
id: rna_differential_expression
modality: rna
label: RNA Differential Expression
eval_weights:
  fdr_calibration: 0.4
  lfc_accuracy: 0.3
  ranking_auprc: 0.3
---
Identifies genes significantly up- or down-regulated between cell populations or experimental conditions. Produces a ranked gene list with fold changes and statistical significance.

DE can be run at multiple levels: between clusters (marker genes), between conditions within a cell type, or between time points.

Stages (in order):
- [[stages/qc]] [includes]
- [[stages/normalize]] [includes]
- [[stages/feature_selection]] [includes]
- [[stages/embed]] [includes]
- [[stages/cluster]] [includes]
- [[stages/annotate]] [includes]
- [[stages/de]] [includes]

Evaluated by:
- [[tools/eval_de_metrics]] [evaluated_by]

Key decisions for the consultant:
- **Pseudobulk** (default when `donor_key` is present and ≥3 donors per group): most statistically valid; uses PyDESeq2
- **Wilcoxon** (default when no `donor_key`): fast marker discovery; use for single-sample or exploratory analysis
- **MAST**: use when pseudobulk is not possible (< 3 donors) but donor correction is needed
- The `contrast` parameter specifies comparison: `["condition", "treated", "control"]` or cluster IDs
- Raw counts (`adata.layers["counts"]`) must be present for pseudobulk
