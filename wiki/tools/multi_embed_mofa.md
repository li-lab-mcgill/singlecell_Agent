---
type: tool
id: multi_embed_mofa
modality: multi
stage: embed
backend: backend/tools/multi/embed/mofa.py
label: Multi-omic Factor Decomposition (MOFA+)
default: false
params:
  n_factors: 20
  n_epochs: 1000
  convergence_mode: fast
---

Decomposes paired RNA+ATAC variation into interpretable latent factors using MOFA+ (Multi-Omics Factor Analysis v2). Unlike MultiVI/WNN which produce embeddings for clustering, MOFA+ is used when factor interpretability and understanding which sources of variation are shared vs modality-specific is the goal.

Key parameters:
- `atac_h5ad_path` (default None)
- `n_factors` (default 20)
- `n_epochs` (default 1000)
- `convergence_mode` (default "fast")
- `use_gpu` (default False)

**Outputs:**
- `adata.obsm["X_mofa"]`: factor scores (cells × n_factors)
- `adata.varm["mofa_loadings_rna"]`: gene loadings per factor
- `adata.uns["mofa"]`: metadata including variance explained per factor

**When to use:**
- When you want to understand *what* drives variation (factor interpretation) rather than just clustering
- When identifying shared vs. modality-specific sources of variation
- When integrating more than 2 modalities (MOFA+ supports arbitrary numbers)
- Not ideal as the primary clustering embedding — use MultiVI or WNN for that

**Params:**
- `atac_h5ad_path`: path to ATAC AnnData
- `n_factors`: number of latent factors (default 20; use elbow on variance explained)
- `n_epochs`: max training iterations (default 1000)
- `convergence_mode`: "fast" (default), "medium", or "slow"
- `use_gpu`: use GPU if available (default False)

Package: MOFA+ / mofapy2
Method: [[methods/mofa_programs]] [multi]
