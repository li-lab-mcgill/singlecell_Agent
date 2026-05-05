---
type: package
id: bbknn
version: ">=1.5"
citation: Polański et al. 2020 Bioinformatics
---

BBKNN (Batch Balanced K-Nearest Neighbors) builds a batch-corrected neighbor graph by finding k nearest neighbors within each batch rather than globally. It does not produce a corrected embedding — it directly modifies the neighbor graph used for clustering and UMAP.

Install: `pip install bbknn`

BBKNN is particularly effective when batches have very different cell type compositions, where embedding-based correction methods like Harmony may fail. It is faster than Harmony for large datasets. [Polański et al. 2020]

Key difference from Harmony: BBKNN corrects the graph, not the embedding. UMAP computed after BBKNN will be batch-corrected but `adata.obsm["X_pca"]` remains uncorrected. Use Harmony when you need a corrected embedding for downstream analysis; use BBKNN when you only need batch-corrected clustering and visualization.

Parameter `neighbors_within_batch` (default 3): number of neighbors from each batch. Increase for datasets with many batches.
