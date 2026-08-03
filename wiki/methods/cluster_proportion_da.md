---
type: method
id: cluster_proportion_da
label: Cluster Proportion Differential Abundance
---

Cluster proportion DA compares the fraction of cells in each cluster per sample between conditions. It is simpler than Milo but requires prior clustering and misses effects that span cluster boundaries.

Workflow:
1. Count cells per cluster per sample → (samples × clusters) proportion matrix
2. Test each cluster: compare proportions between conditions using a t-test, Wilcoxon test, or compositional model (e.g., `sccomp`, `speckle`)

**sccomp**: Bayesian compositional model that accounts for the constraint that proportions sum to 1 and models overdispersion. Most statistically rigorous.

**speckle (propeller)**: uses logit-transformed proportions + limma; fast and widely used.

Simple t-test on proportions: quick exploratory analysis; valid only when sample sizes are equal and proportions are not near 0 or 1.

Requirements: multiple samples per condition (≥3). Single-cell data without biological replicates cannot provide valid DA testing.

Edges:
No executable backend tool currently implements cluster-proportion DA.
