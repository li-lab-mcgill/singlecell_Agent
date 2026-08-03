---
type: tool
id: rna_batch_integration_scanorama
stage: batch_integration
modality: rna
backend: backend/tools/rna/batch_integration/scanorama.py
---

Integrates multiple scRNA-seq datasets by finding shared cell populations across batches and aligning them in a joint embedding space using Scanorama's panoramic stitching algorithm.

Key parameters:
- `batch_key` (required)
- `n_components` (default 50)

Scanorama operates on the log-normalized expression matrix (not PCA). It finds mutual nearest neighbors across batches in expression space, then aligns the batches using manifold intersection.

Stores result in `adata.obsm["X_scanorama"]`. Use this as the `use_rep` for downstream clustering.

Best suited for datasets where batches share only a subset of cell types (partial overlap). For full cell type overlap, Harmony is faster and equally good.

Package: [[packages/scanorama]]
Method: [[methods/embedding_correction]]
