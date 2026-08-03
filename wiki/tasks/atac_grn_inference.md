---
type: task
id: atac_grn_inference
modality: atac
label: ATAC Gene Regulatory Network Inference
eval_weights:
  network_auprc: 0.5
  tf_activity_correlation: 0.5
---
Infers TF → target gene regulatory networks using chromatin accessibility data. ATAC-based GRN inference uses motif occurrence in peaks as direct evidence of TF binding, providing cis-regulatory support that RNA-only methods lack.

Stages (in order):
- [[stages/qc]] [includes]
- [[stages/peak_calling]] [includes]
- [[stages/feature_selection]] [includes]
- [[stages/embed]] [includes]
- [[stages/cluster]] [includes]
- [[stages/peak_to_gene]] [includes]
- [[stages/motif]] [includes]
- [[stages/grn_inference]] [includes]

Evaluated by:
No dedicated executable GRN evaluation tool is currently registered.

Key decisions for the consultant:
- **decoupler with chromatin accessibility**: use motif scanning output as TF activity matrix — this is the ATAC analog of CollecTRI-based RNA activity scoring
- **pySCENIC (ctx step on ATAC peaks)**: if paired RNA is available, use pySCENIC with ATAC peaks as the cis-regulatory database instead of the default motif rankings
- **SnapATAC2 integrated pipeline**: uses motif scanning + peak-gene links to build TF → peak → gene chains
- For pure ATAC-only GRN, the output is a TF → peak → gene chain rather than a direct TF → gene link
