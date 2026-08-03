---
type: tool
id: rna_de_edger
stage: de
modality: rna
backend: backend/tools/rna/de/edger.py
---

Performs pseudobulk differential expression using edgeR's quasi-likelihood (QL) framework via R/rpy2. An alternative to PyDESeq2 with slightly different statistical properties.

Key parameters:
- `group_key` (required)
- `sample_key` (required)
- `reference` (default "rest")
- `top_n` (default 50)

edgeR QL pipeline:
1. Estimate dispersion: `estimateDisp()` → common, trended, tagwise dispersion
2. Fit QL model: `glmQLFit()`
3. Test: `glmQLFTest()` with contrast vector

Output: DataFrame with `logFC`, `PValue`, `FDR` per gene.

edgeR and DESeq2 give very similar results for well-powered studies. edgeR is slightly better calibrated for small sample sizes (2–3 replicates per group). Requires R and the `edgeR` Bioconductor package.

Package: [[packages/statsmodels]] (R edgeR via rpy2)
Method: [[methods/pseudobulk_de]]
