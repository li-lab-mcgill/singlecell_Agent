---
type: stage
id: embed
label: Embedding
---

The embedding stage computes a low-dimensional representation of cells that captures biological variation while compressing noise. The resulting embedding is used as input for clustering, visualization, and trajectory analysis.

For RNA, PCA on HVGs is the standard linear embedding. For ATAC, spectral embedding (LSI/TF-IDF + SVD) is standard. Deep generative models like scVI produce non-linear embeddings that also handle batch effects.

The output embedding key (e.g., `X_pca`, `X_scvi`, `X_spectral`) must be passed to downstream stages.

Edges:
- [[methods/linear_embedding]] modality: rna, multi
- [[methods/deep_generative_embedding]] modality: rna, multi
- [[methods/spectral_embedding]] modality: atac, multi
- [[methods/joint_embedding]] modality: multi
