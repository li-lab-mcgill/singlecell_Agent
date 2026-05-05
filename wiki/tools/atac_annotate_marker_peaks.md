---
type: tool
id: atac_annotate_marker_peaks
stage: annotate
modality: atac
backend: backend/tools/atac/annotate/marker_peaks.py
---

Annotates ATAC clusters by identifying cluster-specific accessible peaks near known cell-type marker gene loci, then assigning cell types based on these accessibility patterns.

Key parameters:
- `cluster_key` (default "atac_leiden_clusters"): cluster column to annotate
- `marker_genes` (required): dict mapping cell type names to lists of marker genes; e.g., `{"T cell": ["CD3D", "CD3E"], "B cell": ["CD79A", "MS4A1"]}`
- `genome` (default "hg38"): reference genome for TSS coordinate lookup
- `window` (default 50000): search window around marker gene TSS for accessible peaks

For each cluster, scores the overlap between top-accessible peaks and peaks near each cell type's marker genes. Assigns the cell type with the highest overlap score.

Output: `adata.obs["marker_peak_cell_type"]` — per-cluster annotation.

Package: [[packages/snapatac2]]
Method: [[methods/marker_based_annotation]]
