---
type: task
id: rna_gene_programs
modality: rna
label: RNA Gene Program Discovery
eval_weights:
  program_stability: 0.4
  program_interpretability: 0.3
  reconstruction_error: 0.3
---
Identifies coordinated gene expression programs (modules) that represent underlying biological processes — pathways, regulatory programs, stress responses, or cell cycle effects.

Unlike clustering, gene programs are not mutually exclusive. A single cell can express multiple programs simultaneously. This provides finer-grained insight into transcriptional heterogeneity within clusters.

Stages (in order):
- [[stages/qc]] [includes]
- [[stages/normalize]] [includes]
- [[stages/feature_selection]] [includes]
- [[stages/gene_programs]] [includes]

Evaluated by:
- [[tools/eval_program_metrics]] [evaluated_by]

Key decisions for the consultant:
- **cNMF** (default): consensus NMF; most commonly used for scRNA-seq gene programs
- K (number of programs): run multiple K values (5–20); choose based on instability and error plots
- Use raw counts for cNMF (models the count distribution); log-normalized data is also acceptable but less principled
- Programs should be annotated by inspecting top-weighted genes per program against GO/KEGG databases
