---
type: task
id: multiomic_integration
modality: multi
label: Multi-omic Integration
eval_weights:
  ilisi: 0.20
  clisi: 0.20
  modality_alignment: 0.30
  bio_conservation: 0.30
---
Integrates paired or unpaired RNA and ATAC data from the same cells or matched samples into a unified representation. Produces a joint embedding and clusters that reflect both transcriptomic and epigenomic information.

Stages (in order):
- [[stages/qc]] [includes]
- [[stages/normalize]] [includes]
- [[stages/feature_selection]] [includes]
- [[stages/peak_calling]] [includes]
- [[stages/intersect]] [includes]
- [[stages/embed]] [includes]
- [[stages/cluster]] [includes]
- [[stages/project]] [includes]

Evaluated by:
- [[tools/eval_ari_nmi]] [evaluated_by]
- [[tools/eval_silhouette]] [evaluated_by]
- [[tools/eval_ilisi_clisi]] [evaluated_by]

Key decisions for the consultant:
- **MultiVI** (default for 10x Multiome paired RNA+ATAC): deep generative model; joint latent space handles batch correction via `batch_key`
- **WNN** (default when MultiVI fails or for unpaired data): modality-weighted KNN graph; more flexible; does not require paired measurements
- **MOFA+**: use when the goal is factor decomposition rather than clustering; identifies shared and modality-specific variation
- QC must be run separately for RNA and ATAC modalities before integration
- Ensure cell barcodes are aligned between modalities (`muon.pp.intersect_obs()`)
