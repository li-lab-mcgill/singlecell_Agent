---
type: tool
id: atac_embed_lsi
stage: embed
modality: atac
backend: backend/tools/atac/embed/lsi.py
---

Computes spectral embedding (TF-IDF + truncated SVD) on the ATAC peak or tile matrix. Equivalent to LSI (Latent Semantic Indexing) in other ATAC tools.

Key parameters:
- `lsi_method` (default "tfidf_lsi_v3")
- `n_components` (default 50)
- `drop_first` (default True)
- `binarize` (default True)
- `random_seed` (default 0)
- `scale_factor` (default 10000.0)

Workflow:
1. TF-IDF normalization of the binary/count peak matrix
2. Truncated SVD via `sklearn.utils.extmath.randomized_svd`
3. Cosine normalization of the resulting components

Stores result in `adata.obsm["X_lsi"]` by default. Component 1 is often correlated with sequencing depth, so `drop_first=True` discards it by default.

Package: [[packages/snapatac2]]
Method: [[methods/spectral_embedding]]
