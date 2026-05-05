---
type: stage
id: project
label: Dimensionality Projection
---

The projection stage computes 2D or 3D coordinates for visualization. It takes the embedding (corrected or uncorrected) as input and produces a layout stored in `adata.obsm["X_umap"]` or `adata.obsm["X_tsne"]`.

UMAP is the standard visualization for single-cell data. t-SNE is an alternative that can reveal cluster sub-structure more clearly at the cost of global structure. ForceAtlas2 is used in some trajectory workflows.

This stage is visualization-only. Clustering and annotation should be performed on the embedding, not on the 2D projection. Never use UMAP coordinates as features for downstream analysis.

Edges:
- [[methods/nonlinear_projection]] modality: rna, atac, multi
