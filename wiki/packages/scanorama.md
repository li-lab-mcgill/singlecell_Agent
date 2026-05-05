---
type: package
id: scanorama
version: ">=1.7"
citation: Hie et al. 2019 Nature Biotechnology
---

Scanorama performs panoramic integration of single-cell datasets by finding shared cell populations across batches and aligning them in a joint embedding space. Unlike Harmony, it operates on expression matrices rather than precomputed embeddings.

Install: `pip install scanorama`

Scanorama is well-suited for datasets where batches share only a subset of cell types (partial overlap). It produces a joint `X_scanorama` embedding that can be used for clustering and visualization. [Hie et al. 2019]

Key limitation: requires expression matrices, not arbitrary embeddings. Works best after log-normalization but before PCA. For datasets with full cell type overlap, Harmony typically outperforms Scanorama in speed and quality.

Output stored in `adata.obsm["X_scanorama"]`.
