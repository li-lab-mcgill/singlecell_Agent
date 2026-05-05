---
type: resource
id: pbmc_multiome_10k
modality: multi
source: 10x Genomics
url: https://www.10xgenomics.com/resources/datasets/10k-human-pbmcs-atac-plus-gene-expression-sequencing
---

10,000 human peripheral blood mononuclear cells (PBMCs) profiled with 10x Multiome (simultaneous RNA-seq + ATAC-seq from the same cell). Standard benchmark dataset for multi-omic integration methods.

Key properties:
- Cells: ~10,000 PBMCs from a healthy donor
- Modalities: paired RNA (gene expression) + ATAC (chromatin accessibility)
- Ground truth: well-characterized PBMC cell types (T cells, B cells, NK cells, monocytes, dendritic cells, etc.)
- Format: 10x HDF5 files (.h5) for RNA and ATAC; fragment file for ATAC

Typical cell type composition: CD4 T cells (~35%), CD8 T cells (~15%), NK cells (~10%), B cells (~10%), classical monocytes (~15%), non-classical monocytes (~5%), dendritic cells (~3%), other (~7%).

Used as the test dataset for the `multiomic_integration`, `multi_batch_correction`, and `multi_cell_type_annotation` tasks.

Load with: `muon.read_10x_h5("pbmc_granulocyte_sorted_10k_filtered_feature_bc_matrix.h5")`
