---
type: tool
id: rna_de_wilcoxon
stage: de
modality: rna
backend: backend/tools/rna/de/wilcoxon.py
---

Performs differential expression using the Wilcoxon rank-sum test via `sc.tl.rank_genes_groups()`.

Key parameters:
- `groupby` (required): `adata.obs` column defining groups (cluster labels or condition)
- `groups` (default "all"): which groups to test; if "all", tests each group vs. all others; pass a list for specific contrasts
- `reference` (default "rest"): comparison group; "rest" = all other cells; set to a specific group for pairwise comparison
- `n_genes` (default 100): number of top genes to store per group
- `use_raw` (default True): use `adata.raw` if available (stores pre-HVG filtered data)

Output stored in `adata.uns["rank_genes_groups"]` with keys: `names`, `scores`, `logfoldchanges`, `pvals`, `pvals_adj`.

Statistical caveat: this test is not valid for multi-donor studies — each cell is treated as an independent observation, inflating the false positive rate. Use `rna_de_pseudobulk` when multiple donors are present.

Package: [[packages/scanpy]]
Method: [[methods/statistical_de]]
