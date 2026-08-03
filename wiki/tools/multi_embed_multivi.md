---
type: tool
id: multi_embed_multivi
modality: multi
stage: embed
backend: backend/tools/multi/embed/multivi.py
label: Joint RNA+ATAC Embedding (MultiVI)
default: true
params:
  n_latent: 20
  n_epochs: 500
---

Trains a MultiVI deep generative model on paired RNA+ATAC data to produce a joint latent embedding. MultiVI models both the negative-binomial distribution of RNA counts and the Bernoulli distribution of ATAC peak accessibility, producing a unified representation.

Key parameters:
- `atac_h5ad_path` (default None)
- `batch_key` (default None)
- `n_latent` (default 20)
- `n_epochs` (default 500)
- `use_gpu` (default True)

**Outputs:**
- `adata.obsm["X_multivi"]`: joint latent representation (cells × n_latent)

**When to use:**
- Default for 10x Multiome or other paired RNA+ATAC data
- When batch correction is needed (pass `batch_key`) — MultiVI handles it within the model
- When downstream analysis requires a unified embedding for clustering and UMAP

**Params:**
- `atac_h5ad_path`: path to the paired ATAC h5ad file (required if not already stored in `adata.uns["atac_h5ad_path"]` by `multi_qc_intersect`)
- `batch_key`: adata.obs column for batch correction (optional)
- `n_latent`: latent space dimensionality (default 20)
- `n_epochs`: training epochs (default 500; 200 for quick exploration)

Prerequisite: `multi_qc_intersect` must have been run to align barcodes.

Package: [[packages/scvi_tools]]
Method: [[methods/deep_generative_embedding]] [multi]
