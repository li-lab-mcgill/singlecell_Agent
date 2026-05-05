---
type: method
id: mixed_model_de
label: Mixed Model Differential Expression
---

Mixed model DE uses a linear mixed effects model (LMM) with donor as a random effect to account for within-donor cell correlation while retaining cell-level granularity. It is an alternative to pseudobulk when insufficient donors are available for DESeq2.

The model formula: `expression ~ condition + (1 | donor)`
- Fixed effect: condition (e.g., treatment vs. control)
- Random effect: donor (captures baseline donor differences)

Implementation options:
- **MAST** (via R/rpy2 or Python wrapper): hurdle model for scRNA-seq; models both detection probability and expression level; widely used in published studies
- **statsmodels MixedLM**: pure Python; simpler Gaussian LMM; appropriate for log-normalized data
- **diffxpy wald()**: supports formula-based design with random effects

When to use mixed model vs pseudobulk:
- Fewer than 3 donors per group → pseudobulk fails, use mixed model
- Single-sample paired comparisons → mixed model
- Very large datasets where pseudobulk loses power → mixed model retains cell-level resolution

Key limitation: standard LMMs assume normality of residuals, which is violated for count data. Hurdle models (MAST) handle this better by modeling the zero-inflation separately.

Edges:
- [[tools/rna_de_mast]] implements
