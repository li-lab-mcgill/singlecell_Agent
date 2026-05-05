---
type: tool
id: rna_de_mast
stage: de
modality: rna
backend: backend/tools/rna/de/mast.py
---

Performs differential expression using MAST (Model-based Analysis of Single Cell Transcriptomics), a hurdle model that accounts for both zero-inflation and continuous expression variation with donor as a random effect.

Key parameters:
- `groupby` (required): `adata.obs` column defining groups
- `contrast` (required): `["group", "test", "reference"]`
- `donor_key` (default None): if provided, includes donor as a random effect in the model
- `covariates` (default None): list of additional `adata.obs` columns to include as fixed effects
- `n_cores` (default 4): parallel cores for per-gene model fitting

MAST models each gene with a two-component hurdle model:
1. Discrete component: logistic regression for detection probability
2. Continuous component: linear regression for expression level given detection

Combining both components gives a combined test statistic and p-value.

Use when: fewer than 3 donors per group (pseudobulk fails), or when a mixed model with donor correction is needed for a cell-level test.

Package: [[packages/statsmodels]] (Python reimplementation; or R MAST via rpy2)
Method: [[methods/mixed_model_de]]
