---
type: method
id: graph_correction
label: Graph-based Batch Correction
---

Graph-based batch correction modifies the k-nearest neighbor graph directly, without changing the underlying embedding. It produces a batch-balanced graph where each cell is connected to its nearest neighbors drawn proportionally from all batches.

**BBKNN** (Batch Balanced KNN) is the primary method. For each cell, it finds the `neighbors_within_batch` nearest neighbors from each batch, then merges these into a single neighbor list. This prevents cells from being exclusively connected to cells of the same batch.

Key difference from Harmony: BBKNN modifies `adata.obsp["connectivities"]` and `adata.obsp["distances"]`. The embedding (`adata.obsm["X_pca"]`) is unchanged. Leiden clustering and UMAP computed after BBKNN will be batch-corrected, but the PCA coordinates are still batch-affected.

Use BBKNN when:
- Batches have very different cell type compositions (Harmony can fail in this case)
- You need batch-corrected clustering but want to keep the original embedding for other analyses
- Speed is a priority (BBKNN is faster than Harmony for large datasets)

Edges:
- [[tools/rna_batch_integration_bbknn]] implements
