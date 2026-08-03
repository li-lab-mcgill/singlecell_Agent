---
type: tool
id: rna_de_mast
stage: de
modality: rna
backend: backend/tools/rna/de/mast.py
---

Performs differential expression using MAST (Model-based Analysis of Single Cell Transcriptomics), a hurdle model that accounts for both zero-inflation and continuous expression variation with donor as a random effect.

Key parameters:
- `group_key` (required)
- `reference` (default "rest")
- `top_n` (default 50)

MAST models each gene with a two-component hurdle model:
1. Discrete component: logistic regression for detection probability
2. Continuous component: linear regression for expression level given detection

Combining both components gives a combined test statistic and p-value.

Use when: fewer than 3 donors per group (pseudobulk fails), or when a mixed model with donor correction is needed for a cell-level test.

Package: [[packages/statsmodels]] (Python reimplementation; or R MAST via rpy2)
Method: [[methods/mixed_model_de]]
