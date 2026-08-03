---
type: tool
id: rna_embed_scvi
stage: embed
modality: rna
backend: backend/tools/rna/embed/scvi.py
---

Trains an scVI model and extracts the latent embedding into `adata.obsm["X_scvi"]`. When `batch_key` is provided, also performs batch correction within the latent space.

Key parameters:
- `batch_key` (default None)
- `n_latent` (default 30)
- `n_layers` (default 2)
- `n_epochs` (default None)
- `random_seed` (default 42)
- `accelerator` (default "auto")
- `devices` (default "auto")
- `precision` (default None)

Requires raw counts in `adata.layers["counts"]`. Do not pass log-normalized data.

When `batch_key` is set, scVI learns a batch-invariant latent space. The resulting `X_scvi` embedding can be used directly for clustering without a separate Harmony step.

Package: [[packages/scvi_tools]]
Method: [[methods/deep_generative_embedding]]
