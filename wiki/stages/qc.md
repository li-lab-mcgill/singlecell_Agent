---
type: stage
id: qc
label: Quality Control
---

The QC stage filters out low-quality cells and potential artifacts before any downstream analysis. It is the first stage in every single-cell pipeline regardless of modality.

Common QC failure modes that this stage catches:
- Empty droplets (low total counts, low gene count)
- Dying or damaged cells (high mitochondrial gene fraction for RNA; low TSS enrichment for ATAC)
- Doublets (abnormally high counts suggesting two cells captured together)

Edges:
- [[methods/basic_filter]] modality: rna, atac, multi
- [[methods/doublet_detection]] modality: rna, multi
