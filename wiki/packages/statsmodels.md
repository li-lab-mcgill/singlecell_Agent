---
type: package
id: statsmodels
version: ">=0.14"
citation: Seabold & Perktold 2010 SciPy
---

statsmodels provides statistical models and tests used for differential expression with mixed effects and for compositional analysis.

Install: `pip install statsmodels`

Key usage in single-cell pipelines:

- **Mixed linear model (DE)**: `statsmodels.regression.mixed_linear_model.MixedLM` — fits LMM with donor as random effect; used for DE when pseudobulk is not possible (insufficient replicates)
- **Negative binomial GLM**: `statsmodels.genmod.families.NegativeBinomial` — GLM for count data; used for differential abundance testing without Milo
- **Multiple testing correction**: `statsmodels.stats.multitest.multipletests` — Benjamini-Hochberg FDR correction; standard use: `multipletests(pvals, method="fdr_bh")`

For mixed model DE, the typical formula is:
```python
import statsmodels.formula.api as smf
model = smf.mixedlm("expression ~ condition", data=df, groups=df["donor"])
result = model.fit()
```

statsmodels is a dependency utility — it is not called directly by the user but is used internally by DE and DA tools in the pipeline.
