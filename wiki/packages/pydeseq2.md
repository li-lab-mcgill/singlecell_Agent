---
type: package
id: pydeseq2
version: ">=0.4"
citation: Love et al. 2014 Genome Biology; Muzellec et al. 2023
---

PyDESeq2 is a Python reimplementation of DESeq2 for bulk and pseudobulk differential expression analysis. It uses negative binomial regression with shrinkage estimators for dispersion and log fold change.

Install: `pip install pydeseq2`

PyDESeq2 is the recommended tool for pseudobulk DE in single-cell workflows. The pseudobulk approach aggregates raw counts per donor×cell-type combination to create pseudo-samples, then runs standard bulk DE. This properly accounts for repeated measures within donors and avoids the inflated false positive rate of cell-level tests.

Key usage:
```python
from pydeseq2.dds import DeseqDataSet
from pydeseq2.ds import DeseqStats

dds = DeseqDataSet(counts=pseudobulk_counts, metadata=sample_meta, design_factors="condition")
dds.deseq2()
stat_res = DeseqStats(dds, contrast=["condition", "treated", "control"])
stat_res.summary()
results_df = stat_res.results_df
```

Output columns: `baseMean`, `log2FoldChange`, `lfcSE`, `stat`, `pvalue`, `padj`.

Key limitation: requires at least 3 samples per group for reliable dispersion estimation. For datasets with fewer replicates, use MAST or a mixed model approach instead.
