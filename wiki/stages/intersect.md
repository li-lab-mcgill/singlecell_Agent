---
type: stage
id: intersect
label: Modality Intersection / Barcode Alignment
---

Aligns cell barcodes between RNA and ATAC AnnData objects so that only cells present in both modalities are kept. Required before any joint embedding step (MultiVI, WNN, MOFA+).

This stage is multi-omic specific. It is always run after per-modality QC and before the embed stage in multi-omic pipelines.

Edges:
- [[methods/barcode_intersection]] [multi]
