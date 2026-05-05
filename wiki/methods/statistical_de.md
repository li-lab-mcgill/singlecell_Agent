---
type: method
id: statistical_de
label: Statistical Differential Expression (Cell-level)
---

Cell-level statistical DE tests directly compare expression distributions between groups at the individual cell level. These tests are fast and widely used for marker gene discovery.

**Wilcoxon rank-sum test**: `sc.tl.rank_genes_groups(method="wilcoxon")` — non-parametric; does not assume normal distribution; standard for marker gene discovery. Fast, robust, no covariates.

**t-test**: `sc.tl.rank_genes_groups(method="t-test_overestim_var")` — parametric; assumes normality; slightly more power than Wilcoxon but sensitive to outliers.

**Logistic regression**: `sc.tl.rank_genes_groups(method="logreg")` — models cluster membership as a function of gene expression; handles multiclass naturally.

Statistical caveat: cell-level tests treat each cell as an independent observation, which is invalid when cells come from the same donor. This leads to severely inflated false positive rates in multi-donor studies. For multi-donor DE, always use pseudobulk methods instead.

Cell-level tests are appropriate for: (1) single-sample exploratory analysis, (2) finding marker genes within a single donor, (3) quick hypothesis generation.

Output: `adata.uns["rank_genes_groups"]` with per-cluster gene rankings, log fold changes, p-values, and adjusted p-values.

Edges:
- [[tools/rna_de_wilcoxon]] implements
