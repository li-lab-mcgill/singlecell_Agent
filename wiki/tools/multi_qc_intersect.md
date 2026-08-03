---
type: tool
id: multi_qc_intersect
modality: multi
stage: intersect
backend: backend/tools/multi/qc/intersect.py
label: Multi-omic Cell Intersection QC
default: true
params: {}
---

Intersects cells present in both RNA and ATAC AnnData objects, keeping only shared barcodes. Must be the first step in any multi-omic pipeline before joint embedding.

Key parameters:
- `atac_h5ad_path` (required)
- `output_atac_h5ad_path` (default None)

**Why this is needed:** 10x Multiome and other paired protocols can have barcodes present in one modality but not the other due to QC filtering applied independently. Running embedding on misaligned cells will fail or produce incorrect results.

**Outputs:**
- RNA adata subsetted to shared cells
- ATAC AnnData subsetted and reordered to match RNA barcodes
- `adata.uns["multi_qc"]`: dict with n_shared, n_dropped_rna, n_dropped_atac

**Params:**
- `atac_h5ad_path`: path to ATAC AnnData h5ad file (required)

Package: [[packages/muon]]
Method: [[methods/barcode_intersection]] [multi]
