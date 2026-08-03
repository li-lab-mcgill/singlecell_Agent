---
type: tool
id: atac_annotate_marker_peaks
stage: annotate
modality: atac
backend: backend/tools/atac/annotate/marker_peaks.py
---

Annotates ATAC clusters by identifying cluster-specific accessible peaks near known cell-type marker gene loci, then assigning cell types based on these accessibility patterns.

Key parameters:
- `group_key` (required)
- `marker_peaks` (required)
- `min_score` (default 0.0)

For each cluster, scores the overlap between top-accessible peaks and peaks near each cell type's marker genes. Assigns the cell type with the highest overlap score.

Output: `adata.obs["marker_peak_cell_type"]` — per-cluster annotation.

Package: [[packages/snapatac2]]
Method: [[methods/marker_based_annotation]]
