---
type: task
id: multi_grn_inference
modality: multi
label: Multi-omic GRN Inference
eval_weights:
  network_auprc: 0.4
  tf_activity_correlation: 0.3
  regulon_chromatin_support: 0.3
---
Infers gene regulatory networks using both RNA expression and ATAC chromatin accessibility. Multi-omic GRN inference is the most comprehensive approach — it combines co-expression from RNA with cis-regulatory evidence from ATAC.

The network chain: TF → accessible peak (motif evidence) → target gene (correlation evidence) → validated by TF expression correlation.

Stages (in order):
- [[stages/qc]] [includes]
- [[stages/normalize]] [includes]
- [[stages/feature_selection]] [includes]
- [[stages/peak_calling]] [includes]
- [[stages/intersect]] [includes]
- [[stages/embed]] [includes]
- [[stages/cluster]] [includes]
- [[stages/peak_to_gene]] [includes]
- [[stages/motif]] [includes]
- [[stages/grn_inference]] [includes]

Evaluated by:
- [[tools/eval_grn_metrics]] [evaluated_by]

Key decisions for the consultant:
- **pySCENIC + ATAC peaks**: use peak-gene links as the cis-regulatory database instead of generic motif rankings; most comprehensive
- **SnapATAC2 integrated TF activity**: `snap.tl.motif_scanning()` → per-cell TF activity → correlate with gene expression
- **decoupler + CollecTRI**: fast baseline; RNA-only; use to quickly identify active TFs before running full multi-omic GRN
- Peak-to-gene links should be computed before GRN inference (peak_to_gene stage must precede grn_inference)
- Requires paired RNA+ATAC; unpaired data can only use RNA-based GRN methods
