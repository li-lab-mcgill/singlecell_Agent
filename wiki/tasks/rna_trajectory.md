---
type: task
id: rna_trajectory
modality: rna
label: RNA Trajectory Analysis
eval_weights:
  pseudotime_correlation: 0.5
  trajectory_topology: 0.5
---
Orders cells along a continuous developmental or differentiation trajectory and assigns pseudotime scores. Reveals the progression of cell states and identifies genes that change along the trajectory.

Trajectory analysis is appropriate for biological processes that are continuous — differentiation, activation, maturation. For clearly discrete, stable cell types, clustering and annotation is sufficient.

Stages (in order):
- [[stages/qc]] [includes]
- [[stages/normalize]] [includes]
- [[stages/feature_selection]] [includes]
- [[stages/embed]] [includes]
- [[stages/cluster]] [includes]
- [[stages/project]] [includes]
- [[stages/trajectory]] [includes]

Evaluated by:
- [[tools/eval_trajectory_metrics]] [evaluated_by]

Key decisions for the consultant:
- The root cell must be specified by the user or inferred from known biology (progenitor marker expression)
- **DPT** (default): diffusion pseudotime on the KNN graph; good for simple linear or branching trajectories
- If the user mentions RNA velocity (spliced/unspliced counts available): note that scVelo would be more appropriate; flag this for user confirmation
- After pseudotime: run `sc.tl.rank_genes_groups()` along pseudotime bins to find trajectory-variable genes
