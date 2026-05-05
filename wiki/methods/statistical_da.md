---
type: method
id: statistical_da
label: Statistical Differential Accessibility (Cell-level)
---

Cell-level DA tests compare peak accessibility distributions between groups at the individual cell level. The same statistical caveats as cell-level DE apply: inflated FDR when multiple donors are present.

**Wilcoxon rank-sum**: fast, non-parametric; suitable for single-sample or exploratory analyses.

**Logistic regression**: `sc.tl.rank_genes_groups(method="logreg")` applied to the peak matrix; models cluster membership from accessibility; handles multi-class natively.

**SnapATAC2 diff_test**: logistic regression with pseudo-bulk aggregation per cluster; more conservative than pure cell-level tests.

For ATAC data, peak counts are sparser and more binary than RNA counts. Wilcoxon on binary-ish data has limited power. Logistic regression is often preferred for ATAC.

Output: peak-level statistics with log fold change, p-value, adjusted p-value.

Edges:
- [[tools/atac_da_wilcoxon]] implements
