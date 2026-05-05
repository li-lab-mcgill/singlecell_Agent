---
type: task
id: rna_grn_inference
modality: rna
label: RNA Gene Regulatory Network Inference
eval_weights:
  network_auprc: 0.4
  tf_activity_correlation: 0.3
  regulon_enrichment: 0.3
---
Reconstructs transcription factor → target gene regulatory networks from scRNA-seq data. Identifies which TFs are active in which cell types and their downstream targets.

Stages (in order):
- [[stages/qc]] [includes]
- [[stages/normalize]] [includes]
- [[stages/feature_selection]] [includes]
- [[stages/embed]] [includes]
- [[stages/cluster]] [includes]
- [[stages/grn_inference]] [includes]

Evaluated by:
- [[tools/eval_grn_metrics]] [evaluated_by]

Key decisions for the consultant:
- **decoupler (CollecTRI)** (default): fast, no ATAC required; good for initial TF activity scoring; run first
- **pySCENIC** (when comprehensive network reconstruction is needed): co-expression + motif validation; slower but produces full regulons; requires cisTarget databases
- For RNA-only GRN: decoupler is recommended; pySCENIC adds value when the user wants regulon structure
- For multi-omic GRN (RNA+ATAC): see `multi_grn_inference` task which uses ATAC peaks as cis-regulatory evidence
