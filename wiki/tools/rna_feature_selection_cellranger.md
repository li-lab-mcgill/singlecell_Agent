---
type: tool
id: rna_feature_selection_cellranger
stage: feature_selection
modality: rna
backend: backend/tools/rna/feature_selection/cellranger.py
---

Selects highly variable genes using the Cell Ranger-style dispersion method. Uses normalized dispersion (dispersion divided by mean) to rank genes.

Key parameters:
- `n_top_genes` (default 2000): number of genes to select
- `n_bins` (default 20): number of expression bins for dispersion normalization

This is the original Seurat/Cell Ranger method and is now considered legacy. It tends to select more lowly expressed genes than the Seurat v3 method.

Use when: reproducing older Cell Ranger or Seurat v1/v2 analyses.

Package: [[packages/scanpy]]
Method: [[methods/highly_variable_genes]]
