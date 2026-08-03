---
type: tool
id: multi_embed_wnn
modality: multi
stage: embed
backend: backend/tools/multi/embed/wnn.py
label: Weighted Nearest Neighbor Joint Embedding (WNN)
default: false
params:
  n_neighbors: 20
  n_pcs_rna: 30
  n_pcs_atac: 30
---

Computes a Weighted Nearest Neighbor (WNN) joint graph from separate RNA and ATAC embeddings. WNN assigns per-cell weights to each modality based on its local informativeness, then builds a unified KNN graph used for clustering and UMAP.

Key parameters:
- `atac_h5ad_path` (default None)
- `rna_embedding_key` (default "X_pca")
- `atac_embedding_key` (default "X_lsi")
- `n_neighbors` (default 20)
- `n_pcs_rna` (default 30)
- `n_pcs_atac` (default 30)

**Outputs:**
- WNN joint KNN graph stored in the AnnData connectivity graph

**When to use:**
- When MultiVI fails or is too slow
- For unpaired or partially paired data (RNA and ATAC from the same population but not same cells)
- When modality-specific embeddings are already computed and you want a quick integration

**Prerequisites:**
- RNA PCA must be in `adata.obsm["X_pca"]` (run `rna_embed_pca` first)
- ATAC LSI must be in `atac.obsm["X_lsi"]` (run `atac_embed_lsi` first)
- `multi_qc_intersect` must have been run

**Params:**
- `atac_h5ad_path`: path to the paired ATAC h5ad file (required if not stored in `adata.uns["atac_h5ad_path"]` by `multi_qc_intersect`)
- `rna_embedding_key` (default `"X_pca"`): which RNA embedding to use for WNN; must exist in `adata.obsm`
- `atac_embedding_key` (default `"X_lsi"`): which ATAC embedding to use for WNN; must exist in `atac.obsm`
- `n_neighbors`: KNN graph neighbors (default 20)
- `n_pcs_rna`: PCs from RNA embedding (default 30)
- `n_pcs_atac`: PCs from ATAC embedding (default 30)

Package: [[packages/muon]]
Method: [[methods/joint_embedding]] [multi]
