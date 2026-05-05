---
type: method
id: barcode_intersection
label: Barcode Intersection
---

Retains only cells whose barcodes appear in both the RNA and ATAC AnnData objects. Writes the filtered ATAC h5ad to disk and stores its path in `adata.uns["atac_h5ad_path"]` so downstream multi-omic tools (MultiVI, WNN, MOFA+) can find it automatically.

This is always a prerequisite for multi-omic embedding. Running it ensures cell counts are identical across modalities and prevents the "Modalities cannot be None" and barcode mismatch errors that arise when MultiVI/WNN receive unaligned data.

Edges:
- [[tools/multi_qc_intersect]] implements
