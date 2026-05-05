---
type: tool
id: rna_annotate_cellmarker
stage: annotate
modality: rna
backend: backend/tools/rna/annotate/cellmarker.py
---

Annotates clusters by scoring against the CellMarker 2.0 database of canonical marker genes. For each cluster, computes an overlap score between top cluster markers and each cell type's marker gene set in the database.

Key parameters:
- `cluster_key` (default "leiden_clusters"): cluster column to annotate
- `n_top_genes` (default 20): number of top DE genes per cluster for overlap scoring
- `tissue_filter` (default None): if set, restricts lookup to markers from the specified tissue (e.g., "Blood")
- `species` (default "Human"): species for database lookup; "Mouse" also available

Scores each cluster against all cell types in the database and returns the top-k matches with overlap scores. Does not require API access — uses a local copy of the CellMarker 2.0 database.

Output: `adata.uns["cellmarker_annotation"]` — dict mapping cluster ID to ranked list of `(cell_type, score, matched_genes)` tuples.

Package: [[packages/scanpy]] (via internal lookup table)
Method: [[methods/marker_based_annotation]]
