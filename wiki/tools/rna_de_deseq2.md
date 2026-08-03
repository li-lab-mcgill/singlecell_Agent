---
type: tool
id: rna_de_deseq2
stage: de
modality: rna
backend: backend/tools/rna/de/deseq2.py
---

Performs pseudobulk differential expression using PyDESeq2. Aggregates raw counts per donor×cell-type, then runs DESeq2 negative binomial regression.

Key parameters:
- `group_key` (required)
- `sample_key` (default None)
- `top_n` (default 50)

Output: DataFrame with `log2FoldChange`, `pvalue`, `padj`, `baseMean` per gene; stored in `adata.uns["de_pseudobulk_results"]`.

Requires ≥3 samples per condition for reliable dispersion estimation. Raises a warning if fewer samples are available.

Package: [[packages/pydeseq2]]
Method: [[methods/pseudobulk_de]]
