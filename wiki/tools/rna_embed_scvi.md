---
type: tool
id: rna_embed_scvi
stage: embed
modality: rna
backend: backend/tools/rna/embed/scvi.py
---

Trains an scVI model and extracts the latent embedding into `adata.obsm["X_scvi"]`. When `batch_key` is provided, also performs batch correction within the latent space.

Key parameters:
- `n_latent` (default 30): dimensionality of the latent space
- `n_layers` (default 2): number of hidden layers in the encoder/decoder
- `n_epochs` (default 400): training epochs; reduce to 100–200 for large datasets (>100k cells)
- `batch_key` (default None): if set, batch correction is performed; this replaces the separate Harmony step
- `gene_likelihood` (default "zinb"): `"zinb"` (zero-inflated negative binomial) for dropout-heavy data; `"nb"` for cleaner data
- `layer` (default "counts"): which layer contains raw integer counts

Requires raw counts in `adata.layers["counts"]`. Do not pass log-normalized data.

When `batch_key` is set, scVI learns a batch-invariant latent space. The resulting `X_scvi` embedding can be used directly for clustering without a separate Harmony step.

Package: [[packages/scvi_tools]]
Method: [[methods/deep_generative_embedding]]
