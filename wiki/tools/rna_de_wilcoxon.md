---
type: tool
id: rna_de_wilcoxon
stage: de
modality: rna
backend: backend/tools/rna/de/wilcoxon.py
---

Performs differential expression using the Wilcoxon rank-sum test via `sc.tl.rank_genes_groups()`.

Key parameters:
- `group_key` (required)
- `reference` (default "rest")
- `top_n` (default 50)

Output stored in `adata.uns["rank_genes_groups"]` with keys: `names`, `scores`, `logfoldchanges`, `pvals`, `pvals_adj`.

Statistical caveat: this test is not valid for multi-donor studies — each cell is treated as an independent observation, inflating the false positive rate. Use `rna_de_deseq2` or `rna_de_edger` when multiple donors are present.

Package: [[packages/scanpy]]
Method: [[methods/statistical_de]]
