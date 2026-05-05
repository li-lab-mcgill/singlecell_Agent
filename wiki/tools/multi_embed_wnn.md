---
type: tool
id: multi_embed_wnn
modality: multi
stage: embed
label: Weighted Nearest Neighbor Joint Embedding (WNN)
default: false
params:
  n_neighbors: 20
  n_pcs_rna: 30
  n_pcs_atac: 30
---

Computes a Weighted Nearest Neighbor (WNN) joint graph from separate RNA and ATAC embeddings. WNN assigns per-cell weights to each modality based on its local informativeness, then builds a unified KNN graph used for clustering and UMAP.

**Outputs:**
- `adata.obsm["X_wnn_umap"]`: WNN UMAP embedding (2D)
- `adata.obsp["connectivities"]`: WNN joint KNN connectivities
- `adata.obsp["distances"]`: WNN joint KNN distances

**When to use:**
- When MultiVI fails or is too slow
- For unpaired or partially paired data (RNA and ATAC from the same population but not same cells)
- When modality-specific embeddings are already computed and you want a quick integration

**Prerequisites:**
- RNA PCA must be in `adata.obsm["X_pca"]` (run `rna_embed_pca` first)
- ATAC LSI must be in `atac.obsm["X_lsi"]` (run `atac_embed_spectral` first)
- `multi_qc_intersect` must have been run

**Params:**
- `atac_h5ad_path`: path to ATAC AnnData
- `rna_embedding_key`: RNA embedding to use (default "X_pca")
- `atac_embedding_key`: ATAC embedding to use (default "X_lsi")
- `n_neighbors`: KNN graph neighbors (default 20)
- `n_pcs_rna`: PCs from RNA embedding (default 30)
- `n_pcs_atac`: PCs from ATAC embedding (default 30)

Package: [[packages/muon]]
Method: [[methods/wnn_embedding]] [multi]
