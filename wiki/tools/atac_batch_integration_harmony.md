---
type: tool
id: atac_batch_integration_harmony
stage: batch_integration
modality: atac
backend: backend/tools/atac/batch_integration/harmony.py
---

Corrects batch effects in the ATAC spectral embedding using Harmony. Same algorithm as RNA Harmony but applied to `adata.obsm["X_spectral"]`.

Key parameters:
- `batch_key` (required): `adata.obs` column identifying the batch/donor
- `theta` (default 2.0): diversity penalty; same interpretation as RNA Harmony
- `embedding_key` (default "X_spectral"): which ATAC embedding to correct; uses components 2:N internally to skip the depth component
- `n_comps` (default 49): number of spectral components to use (skips component 1)

Stores corrected embedding in `adata.obsm["X_spectral_harmony"]`. Downstream clustering and UMAP use `use_rep="X_spectral_harmony"`.

Package: [[packages/harmonypy]]
Method: [[methods/embedding_correction]]
