---
type: task
id: rna_batch_correction
modality: rna
label: RNA Batch Correction
eval_weights:
  ilisi: 0.25
  kbet: 0.25
  clisi: 0.25
  scib_composite: 0.25
---
Integrates scRNA-seq data from multiple batches, donors, or experiments into a single corrected embedding where batch effects are minimized and biological variation is preserved.

This task is specifically for multi-batch integration evaluation. Use `rna_clustering` for single-batch datasets or when the goal is cell type identification rather than integration benchmarking.

Stages (in order):
- [[stages/qc]] [includes]
- [[stages/normalize]] [includes]
- [[stages/feature_selection]] [includes]
- [[stages/embed]] [includes]
- [[stages/batch_integration]] [includes]
- [[stages/cluster]] [includes]
- [[stages/project]] [includes]

Evaluated by:
- [[tools/eval_batch_metrics]] [evaluated_by]

Key decisions for the consultant:
- **Harmony** (default): fast, widely used; set `theta` lower (1.0–1.5) if batches have strong biological differences
- **scVI**: better for strong batch effects; requires more compute; use when Harmony leaves residual batch structure
- **BBKNN**: use when batches have very different cell type compositions; graph-corrected only
- **Scanorama**: use when batches share only a subset of cell types
- Always requires `batch_key` to be specified
