---
type: tool
id: rna_de_ttest
stage: de
modality: rna
backend: backend/tools/rna/de/ttest.py
---

Performs differential expression using Welch's t-test via `sc.tl.rank_genes_groups(method="t-test_overestim_var")`.

Key parameters:
- `group_key` (required)
- `reference` (default "rest")
- `top_n` (default 50)

Key parameters: same as `rna_de_wilcoxon` — `group_key`, `reference`, `top_n`.

t-test is slightly faster than Wilcoxon and can have more power for normally distributed data, but is sensitive to outliers and assumes normality. For log-normalized expression data, the normality assumption is approximately met for abundant genes but violated for lowly expressed genes.

Use for quick exploratory comparisons. For publication-quality results, use Wilcoxon or pseudobulk.

Same statistical caveat as Wilcoxon: not valid for multi-donor studies.

Package: [[packages/scanpy]]
Method: [[methods/statistical_de]]
