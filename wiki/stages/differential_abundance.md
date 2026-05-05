---
type: stage
id: differential_abundance
label: Differential Abundance
---

The differential abundance stage tests whether specific cell populations are significantly more or less prevalent in one condition versus another. It addresses compositional changes in the cellular landscape.

Unlike DE (which tests within a cell type) or DA (which tests within genomic regions), differential abundance tests across cell types — the question is "are there more regulatory T cells in disease versus control?"

Two approaches:
- **Cluster-based**: compare cluster proportions per sample using compositional statistics or simple GLM; requires discrete clusters
- **Neighborhood-based (Milo)**: tests at the KNN neighborhood level; detects continuous compositional shifts that don't align with cluster boundaries; requires biological replicates

Milo is preferred for datasets with clear biological replicates. Cluster-proportion tests are acceptable for exploratory analysis.

Edges:
- [[methods/neighborhood_da]] modality: rna, atac, multi
- [[methods/cluster_proportion_da]] modality: rna, atac, multi
