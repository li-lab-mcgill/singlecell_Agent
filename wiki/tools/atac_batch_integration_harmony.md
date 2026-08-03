---
type: tool
id: atac_batch_integration_harmony
stage: batch_integration
modality: atac
backend: backend/tools/atac/batch_integration/harmony.py
---

Corrects batch effects in the ATAC spectral embedding using Harmony. Same algorithm as RNA Harmony but applied to `adata.obsm["X_spectral"]`.

Key parameters:
- `batch_key` (required)
- `embedding_key` (default "X_lsi")
- `theta` (default 2.0)

Stores corrected embedding in `adata.obsm["X_spectral_harmony"]`. Downstream clustering and UMAP use `use_rep="X_spectral_harmony"`.

Package: [[packages/harmonypy]]
Method: [[methods/embedding_correction]]
