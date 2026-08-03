---
type: task
id: atac_batch_correction
modality: atac
label: ATAC Batch Correction
eval_weights:
  ilisi: 0.25
  kbet: 0.25
  clisi: 0.25
  scib_composite: 0.25
---
Integrates scATAC-seq data from multiple batches or donors into a corrected joint embedding.

Stages (in order):
- [[stages/qc]] [includes]
- [[stages/peak_calling]] [includes]
- [[stages/feature_selection]] [includes]
- [[stages/embed]] [includes]
- [[stages/batch_integration]] [includes]
- [[stages/cluster]] [includes]
- [[stages/project]] [includes]

Evaluated by:
- [[tools/eval_ilisi_clisi]] [evaluated_by]
- [[tools/eval_kbet]] [evaluated_by]

Key decisions for the consultant:
- **Harmony on spectral embedding** (default): same approach as RNA but applied to `X_spectral`
- **BBKNN**: use when batches have very different cell type accessibility profiles
- Requires a consensus peak set computed across all batches before batch correction (peaks called per-batch then merged)
- The tile matrix can also be used for batch integration (avoids needing a consensus peak set)
