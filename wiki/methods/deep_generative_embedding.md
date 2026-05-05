---
type: method
id: deep_generative_embedding
label: Deep Generative Embedding (VAE)
---

Deep generative models learn a low-dimensional latent representation of cell expression using a variational autoencoder (VAE). Unlike PCA, VAEs can capture non-linear structure and model the count distribution explicitly.

scVI is the primary implementation. It models raw counts as negative binomial with learned dispersion parameters, making it robust to batch effects when `batch_key` is specified. The latent space captures biological variation with batch effects regressed out.

Key advantages over PCA:
- Handles batch effects natively (batch_key parameter)
- Models count distribution explicitly — no log normalization needed
- Produces a probabilistic embedding with uncertainty estimates
- Scales to millions of cells

Key limitations:
- Slower to train than PCA (minutes to hours depending on dataset size)
- Less interpretable — latent dimensions have no direct gene interpretation
- Requires raw integer counts in `adata.layers["counts"]`

Output stored in `adata.obsm["X_scvi"]`. The scVI model also supports imputation and differential expression via posterior sampling.

When `batch_key` is set, scVI performs joint embedding + batch correction in one step, replacing the separate PCA → Harmony workflow.

Edges:
- [[tools/rna_embed_scvi]] implements
