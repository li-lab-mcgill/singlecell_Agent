---
type: package
id: diffxpy
version: ">=0.7"
citation: Fischer et al. 2019
---

diffxpy is a Python package for differential expression testing in single-cell data. It supports Wald tests, likelihood ratio tests, and t-tests on negative binomial and normal models.

Install: `pip install diffxpy`

diffxpy is well-suited for cell-level DE (not pseudobulk) when donor information is absent or when the dataset is small. For datasets with multiple donors, pseudobulk approaches (PyDESeq2) are statistically preferred.

Key test functions:
- `diffxpy.api.test.wald()` — Wald test on GLM parameters; flexible design matrix
- `diffxpy.api.test.t_test()` — Welch's t-test; fast approximation for exploratory analysis
- `diffxpy.api.test.rank_test()` — Wilcoxon rank-sum test; non-parametric, equivalent to `sc.tl.rank_genes_groups`

The `wald()` test accepts a design matrix formula (e.g., `"~ condition + batch"`) enabling covariate correction — a key advantage over Wilcoxon.

Output: DataFrame with gene-level `pval`, `qval` (BH-adjusted), and `log2fc`.
