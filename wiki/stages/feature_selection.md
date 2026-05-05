---
type: stage
id: feature_selection
label: Feature Selection
---

Feature selection reduces the gene or peak space to the most informative features before embedding, improving signal-to-noise and computational efficiency.

For RNA, highly variable genes (HVGs) capture biological variation while discarding housekeeping genes. For ATAC, the equivalent is selecting highly variable peaks or accessible chromatin regions.

Edges:
- [[methods/highly_variable_genes]] modality: rna, multi
- [[methods/highly_variable_peaks]] modality: atac, multi
