---
type: tool
id: rna_de_pseudobulk
stage: de
modality: rna
backend: backend/tools/rna/de/deseq2.py
---

Performs pseudobulk differential expression using PyDESeq2. Aggregates raw counts per donor×cell-type, then runs DESeq2 negative binomial regression.

Key parameters:
- `groupby` (required): `adata.obs` column for cell groups (cluster or cell type to analyze)
- `group` (required): which group/cell type to run DE for (e.g., `"CD4 T cells"`)
- `sample_key` (required): `adata.obs` column identifying biological replicates/donors
- `condition_key` (required): `adata.obs` column defining the comparison (e.g., `"disease_status"`)
- `contrast` (required): list `["condition", "test_group", "reference_group"]`
- `min_cells` (default 10): minimum cells per sample×group combination; samples with fewer cells are excluded
- `layer` (default "counts"): layer containing raw integer counts

Output: DataFrame with `log2FoldChange`, `pvalue`, `padj`, `baseMean` per gene; stored in `adata.uns["de_pseudobulk_results"]`.

Requires ≥3 samples per condition for reliable dispersion estimation. Raises a warning if fewer samples are available.

Package: [[packages/pydeseq2]]
Method: [[methods/pseudobulk_de]]
