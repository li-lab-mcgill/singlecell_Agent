---
type: method
id: variance_stabilization
label: Variance Stabilization
---

Variance stabilization is an alternative to log-normalization that more rigorously accounts for the mean-variance relationship in count data. It is used when downstream methods are sensitive to heteroscedasticity.

Analytic Pearson residuals (scTransform-style) model each gene's counts as negative binomial, then compute residuals from the expected count given library size. This produces a matrix where variance is independent of mean expression, which benefits PCA.

Two implementations:
- `sc.experimental.pp.normalize_pearson_residuals()` — scanpy's implementation; fast; stores results in `adata.X`
- `scanpy.pp.scale()` — simpler z-score scaling per gene; less statistically principled but still used

For most datasets, log-normalization + HVG selection + PCA performs comparably to Pearson residuals. Pearson residuals are preferred when: (1) library sizes vary dramatically between cells, (2) downstream analysis uses linear regression that assumes constant variance.

Edges:
