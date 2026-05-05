---
type: method
id: spectral_embedding
label: Spectral Embedding (LSI/TF-IDF)
---

Spectral embedding is the standard dimensionality reduction for scATAC-seq. It applies TF-IDF normalization to the binary peak or tile count matrix, then computes a truncated SVD (equivalent to LSI — Latent Semantic Indexing).

TF-IDF (Term Frequency-Inverse Document Frequency) weights peaks by their frequency in a cell and their rarity across all cells, producing a normalized matrix that is not dominated by highly accessible constitutive elements.

The first spectral component (PC1) typically captures sequencing depth variation and is routinely discarded. Use components 2–N for downstream analysis.

Key parameters in SnapATAC2:
- `snap.tl.spectral(adata, n_comps=50)` — default 50 components
- `snap.tl.spectral(adata, features=None)` — uses all peaks; can specify HVP mask

Output stored in `adata.obsm["X_spectral"]`. After batch correction via Harmony, corrected embedding is in `adata.obsm["X_spectral_harmony"]`.

Do not apply log-normalization before spectral embedding. TF-IDF handles the normalization internally and log-transforming sparse binary data before TF-IDF is incorrect.

Edges:
- [[tools/atac_embed_lsi]] implements
