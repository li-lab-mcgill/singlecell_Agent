---
type: tool
id: rna_annotate_cellmarker
stage: annotate
modality: rna
backend: backend/tools/rna/annotate/cellmarker.py
---

Annotates clusters by scoring against the CellMarker 2.0 database of canonical marker genes. For each cluster, computes an overlap score between top cluster markers and each cell type's marker gene set in the database.

Key parameters:
- `refs` (required)
- `obs_cluster` (required)
- `species` (required)
- `tissue_type` (required)
- `cancer_type` (default "Normal")
- `top_n_markers` (default 50)

Scores each cluster against all cell types in the database and returns the top-k matches with overlap scores. Does not require API access — uses a local copy of the CellMarker 2.0 database.

Output: `adata.uns["cellmarker_annotation"]` — dict mapping cluster ID to ranked list of `(cell_type, score, matched_genes)` tuples.

Package: [[packages/scanpy]] (via internal lookup table)
Method: [[methods/marker_based_annotation]]
