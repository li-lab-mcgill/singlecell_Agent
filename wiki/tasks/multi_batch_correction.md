---
type: task
id: multi_batch_correction
modality: multi
label: Multi-omic Batch Correction
eval_weights:
  ilisi: 0.25
  kbet: 0.25
  clisi: 0.25
  scib_composite: 0.25
---
Corrects batch effects in multi-omic (RNA+ATAC) datasets from multiple donors or experiments.

Stages (in order):
- [[stages/qc]] [includes]
- [[stages/normalize]] [includes]
- [[stages/feature_selection]] [includes]
- [[stages/peak_calling]] [includes]
- [[stages/intersect]] [includes]
- [[stages/embed]] [includes]
- [[stages/batch_integration]] [includes]
- [[stages/cluster]] [includes]
- [[stages/project]] [includes]

Evaluated by:
- [[tools/eval_batch_metrics]] [evaluated_by]

Key decisions for the consultant:
- **MultiVI with batch_key** (default): handles batch correction within the joint embedding; most principled for paired RNA+ATAC
- **Harmony per modality then WNN**: correct RNA and ATAC embeddings separately with Harmony, then combine with WNN; more modular
- The joint embedding must be computed first; batch correction is applied either within the joint model (MultiVI) or post-hoc on the separate modality embeddings
