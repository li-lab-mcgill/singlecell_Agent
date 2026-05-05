---
type: task
id: rna_differential_abundance
modality: rna
label: RNA Differential Cell Abundance
eval_weights:
  fdr_calibration: 0.5
  power: 0.5
---
Tests whether specific cell populations are more or less abundant in one condition versus another. Detects compositional shifts in the cellular landscape between disease vs. healthy, treated vs. untreated, etc.

Requires biological replicates (≥3 samples per condition). Not valid for single-sample comparisons.

Stages (in order):
- [[stages/qc]] [includes]
- [[stages/normalize]] [includes]
- [[stages/feature_selection]] [includes]
- [[stages/embed]] [includes]
- [[stages/batch_integration]] [includes]
- [[stages/cluster]] [includes]
- [[stages/project]] [includes]
- [[stages/differential_abundance]] [includes]

Evaluated by:
- [[tools/eval_da_metrics]] [evaluated_by]

Key decisions for the consultant:
- **Milo** (default when ≥3 donors per condition): neighborhood-based; detects continuous shifts; recommended
- **Cluster proportion** (default when clusters are pre-defined and replicates ≥3): simpler; use for quick hypothesis testing
- Milo requires `sample_col` (donor/sample ID) and `design` formula (e.g., `"~ condition"`)
- Batch integration should be run before DA to ensure neighborhoods are not confounded by batch
