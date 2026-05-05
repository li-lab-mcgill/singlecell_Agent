---
type: tool
id: rna_batch_integration_harmony
stage: batch_integration
modality: rna
backend: backend/tools/rna/batch_integration/harmony.py
---

Corrects batch effects by applying Harmony to the PCA embedding. Produces a batch-corrected embedding `adata.obsm["X_harmony"]`.

Key parameters:
- `batch_key` (required): `adata.obs` column identifying the batch/donor
- `theta` (default 2.0): diversity penalty; higher values enforce stronger batch mixing; reduce to 1.0–1.5 for datasets where batches have strong biological differences
- `n_pcs` (default 30): number of PCA components to use as input
- `embedding_key` (default "X_pca"): which embedding to correct; must be present in `adata.obsm`

After running, all downstream tools (clustering, UMAP) should use `use_rep="X_harmony"`.

Harmony does not modify `adata.obsm["X_pca"]` — the original PCA is preserved.

Package: [[packages/harmonypy]]
Method: [[methods/embedding_correction]]
