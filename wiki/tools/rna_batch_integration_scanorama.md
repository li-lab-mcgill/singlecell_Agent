---
type: tool
id: rna_batch_integration_scanorama
stage: batch_integration
modality: rna
backend: backend/tools/rna/batch_integration/scanorama.py
---

Integrates multiple scRNA-seq datasets by finding shared cell populations across batches and aligning them in a joint embedding space using Scanorama's panoramic stitching algorithm.

Key parameters:
- `batch_key` (required): `adata.obs` column identifying the batch
- `n_components` (default 100): dimensionality of the Scanorama joint embedding
- `approx` (default True): use approximate nearest neighbors for speed; disable for small datasets (<5000 cells)
- `sigma` (default 15.0): kernel width for batch alignment; affects how aggressively batches are merged

Scanorama operates on the log-normalized expression matrix (not PCA). It finds mutual nearest neighbors across batches in expression space, then aligns the batches using manifold intersection.

Stores result in `adata.obsm["X_scanorama"]`. Use this as the `use_rep` for downstream clustering.

Best suited for datasets where batches share only a subset of cell types (partial overlap). For full cell type overlap, Harmony is faster and equally good.

Package: [[packages/scanorama]]
Method: [[methods/embedding_correction]]
