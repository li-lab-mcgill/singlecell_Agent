---
type: tool
id: atac_embed_lsi
stage: embed
modality: atac
backend: backend/tools/atac/embed/lsi.py
---

Computes spectral embedding (TF-IDF + truncated SVD) on the ATAC peak or tile matrix. Equivalent to LSI (Latent Semantic Indexing) in other ATAC tools.

Key parameters:
- `n_comps` (default 50): number of spectral components; first component is typically depth-correlated and discarded downstream
- `features` (default None): if None, uses all peaks; if `"selected"`, uses only peaks marked by feature selection
- `distance_metric` (default "cosine"): distance metric for the embedding; cosine is standard for TF-IDF normalized data

Workflow:
1. TF-IDF normalization of the binary/count peak matrix
2. Truncated SVD via `sklearn.utils.extmath.randomized_svd`
3. Cosine normalization of the resulting components

Stores result in `adata.obsm["X_spectral"]`. Component 1 is often correlated with sequencing depth — downstream tools should use components 2–N (`X_spectral[:, 1:]`).

Package: [[packages/snapatac2]]
Method: [[methods/spectral_embedding]]
