---
type: tool
id: multi_embed_multivi
modality: multi
stage: embed
label: Joint RNA+ATAC Embedding (MultiVI)
default: true
params:
  n_latent: 20
  n_epochs: 500
---

Trains a MultiVI deep generative model on paired RNA+ATAC data to produce a joint latent embedding. MultiVI models both the negative-binomial distribution of RNA counts and the Bernoulli distribution of ATAC peak accessibility, producing a unified representation.

**Outputs:**
- `adata.obsm["X_multivi"]`: joint latent representation (cells × n_latent)
- `adata.uns["multivi_model_path"]`: saved model path (if output_dir provided)

**When to use:**
- Default for 10x Multiome or other paired RNA+ATAC data
- When batch correction is needed (pass `batch_key`) — MultiVI handles it within the model
- When downstream analysis requires a unified embedding for clustering and UMAP

**Params:**
- `atac_h5ad_path`: path to ATAC AnnData (reads from `adata.uns["atac_h5ad_path"]` if not given)
- `batch_key`: adata.obs column for batch correction (optional)
- `n_latent`: latent space dimensionality (default 20)
- `n_epochs`: training epochs (default 500; 200 for quick exploration)

Prerequisite: `multi_qc_intersect` must have been run to align barcodes.

Package: [[packages/scvi_tools]]
Method: [[methods/joint_vae_embedding]] [multi]
