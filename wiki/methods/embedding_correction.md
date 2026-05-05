---
type: method
id: embedding_correction
label: Embedding-based Batch Correction
---

Embedding-based batch correction takes a precomputed embedding (PCA or spectral) and returns a corrected embedding of the same dimensionality, where batch-specific variation is reduced while biological variation is preserved.

**Harmony** is the primary method. It iteratively clusters cells and adjusts the embedding to equalize batch composition within clusters. It operates directly on `adata.obsm["X_pca"]` or `adata.obsm["X_spectral"]`.

**Scanorama** is an alternative that finds shared manifolds between batches and aligns them. It operates on expression matrices, not embeddings. Better suited for datasets with partial cell type overlap across batches.

After Harmony correction:
- Corrected embedding stored in `adata.obsm["X_harmony"]` (RNA) or `adata.obsm["X_spectral_harmony"]` (ATAC)
- Raw PCA in `adata.obsm["X_pca"]` is unchanged
- All downstream analysis (clustering, UMAP) uses the corrected embedding

After Scanorama correction:
- Corrected embedding stored in `adata.obsm["X_scanorama"]`

Edges:
- [[tools/rna_batch_integration_harmony]] implements
- [[tools/atac_batch_integration_harmony]] implements
- [[tools/rna_batch_integration_scanorama]] implements
