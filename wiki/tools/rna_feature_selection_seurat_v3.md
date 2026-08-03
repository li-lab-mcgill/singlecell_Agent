---
type: tool
id: rna_feature_selection_seurat_v3
stage: feature_selection
modality: rna
backend: backend/tools/rna/feature_selection/seurat_v3.py
---

Selects highly variable genes using Seurat v3's variance-stabilized method. Equivalent to `sc.pp.highly_variable_genes(flavor="seurat_v3")` but exposes additional Seurat-compatible parameters.

Key parameters:
- `n_top` (default 2000)
- `batch_key` (default None)

The Seurat v3 method selects the most variable genes after variance stabilization, which tends to pick up highly expressed but variable genes more reliably than the original Seurat method.

Use this when: reproducing a Seurat-based analysis, or when the user explicitly requests Seurat v3 HVG selection.

Package: [[packages/scanpy]]
Method: [[methods/highly_variable_genes]]
