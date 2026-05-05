---
type: method
id: mofa_programs
label: MOFA+ Multi-omic Factor Analysis
---

MOFA+ (Multi-Omics Factor Analysis version 2) decomposes variation across multiple data modalities into a set of latent factors. Each factor captures coordinated variation across modalities, and factors can be modality-specific or shared.

MOFA+ is implemented in muon via `muon.tl.mofa()`. It operates on a `MuData` object with RNA and ATAC (and optionally other) modalities.

Workflow:
1. `muon.tl.mofa(mdata, n_factors=10)` — trains the model
2. Factors stored in `mdata.obsm["X_mofa"]`
3. Per-modality variance explained by each factor: `mdata.uns["mofa_variance_explained"]`
4. Gene/peak weights per factor: `mdata.mod["rna"].varm["LFs"]`, `mdata.mod["atac"].varm["LFs"]`

Key outputs:
- `X_mofa`: cell coordinates in factor space (used for clustering / UMAP)
- `LFs` per modality: which genes/peaks drive each factor
- Variance explained: identifies which factors are shared vs. modality-specific

MOFA+ is preferred over NMF for multi-omic data because it explicitly handles missing values (cells with RNA but not ATAC) and provides modality-specific variance decomposition.

Number of factors: start with 10–20; factors explaining < 1% of variance can be discarded.

Edges:
- [[tools/multi_programs_mofa]] implements
