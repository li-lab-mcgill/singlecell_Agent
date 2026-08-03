---
type: tool
id: rna_batch_integration_harmony
stage: batch_integration
modality: rna
backend: backend/tools/rna/batch_integration/harmony.py
---

Corrects batch effects by applying Harmony to the PCA embedding. Produces a batch-corrected embedding `adata.obsm["X_harmony"]`.

Key parameters:
- `batch_key` (required)
- `embedding_key` (default "X_pca")
- `n_pcs` (default 50)
- `theta` (default 2.0)

After running, all downstream tools (clustering, UMAP) should use `use_rep="X_harmony"`.

Harmony does not modify `adata.obsm["X_pca"]` — the original PCA is preserved.

Package: [[packages/harmonypy]]
Method: [[methods/embedding_correction]]
