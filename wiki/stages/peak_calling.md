---
type: stage
id: peak_calling
label: Peak Calling
---

Peak calling converts raw ATAC-seq fragment data into a set of genomic intervals (peaks) representing accessible chromatin regions. It produces the feature space used for all downstream ATAC analysis.

The recommended workflow for single-cell data is pseudo-bulk peak calling: aggregate fragments per cluster (or per cell type), call peaks per cluster with MACS3, then merge into a consensus peak set. This captures cell-type-specific peaks that would be missed by calling on all cells combined.

Peak calling precedes feature matrix construction — the output peak set is used to build the cell × peak count matrix.

Edges:
- [[methods/macs_peak_calling]] modality: atac, multi
