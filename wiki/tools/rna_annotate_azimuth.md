---
type: tool
id: rna_annotate_azimuth
stage: annotate
modality: rna
backend: backend/tools/rna/annotate/azimuth.py
---

Annotates cells using Azimuth reference-based label transfer. Projects query cells onto a Seurat reference atlas and transfers cell type labels based on nearest neighbor assignment in the reference embedding.

Key parameters:
- `reference` (default "pbmcref"): Azimuth reference dataset; options include `"pbmcref"` (PBMC), `"bonemarrowref"`, `"lungref"`, `"kidneyref"`, `"heartref"`
- `label_key` (default "predicted.celltype.l2"): annotation level to transfer; Azimuth provides hierarchical labels (l1 = coarse, l2 = fine, l3 = finest)

Requires internet access to download reference data on first use. References are cached locally.

Output:
- `adata.obs["azimuth_cell_type"]`: transferred label
- `adata.obs["azimuth_score"]`: prediction confidence score

Best suited for tissues with an Azimuth reference. For tissues not covered, use CellTypist or GPT-4.

Package: [[packages/scvi_tools]] (via scvi reference mapping API)
Method: [[methods/reference_based_annotation]]
