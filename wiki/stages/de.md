---
type: stage
id: de
label: Differential Expression
---

The DE stage identifies genes that are significantly up- or down-regulated between two or more cell populations or conditions. It operates on raw or normalized counts.

Three methodological classes:
- **Statistical tests (cell-level)**: Wilcoxon rank-sum, t-test; fast, widely used for marker gene discovery; inflated FDR when donors are present
- **Pseudobulk (donor-level)**: aggregate counts per donor×cell-type, then run DESeq2 or edgeR; statistically rigorous when ≥3 donors per group
- **Mixed model (cell-level with donor correction)**: LMM or MAST with donor as random effect; handles unbalanced designs; slower than pseudobulk

For multi-sample studies with proper replicates, pseudobulk is the gold standard. For single-sample exploratory analysis (e.g., cluster marker discovery), Wilcoxon is acceptable.

Edges:
- [[methods/statistical_de]] modality: rna, multi
- [[methods/pseudobulk_de]] modality: rna, multi
- [[methods/mixed_model_de]] modality: rna, multi
