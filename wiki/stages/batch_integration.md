---
type: stage
id: batch_integration
label: Batch Integration
---

The batch integration stage corrects for technical variation introduced by different experimental batches, donors, or sequencing runs. It is only needed when the dataset contains multiple batches; it should be skipped for single-batch datasets.

Two categories of methods:
- **Embedding correction**: modifies the low-dimensional embedding (Harmony, scVI) — downstream tools use the corrected embedding
- **Graph correction**: modifies the neighbor graph without changing the embedding (BBKNN) — downstream clustering uses the corrected graph but the raw PCA remains available

For RNA and ATAC, embedding correction is preferred unless batches have very different cell type compositions. For multi-omic data, modality-aware methods (MultiVI, WNN) handle batch correction implicitly.

Edges:
- [[methods/embedding_correction]] modality: rna, atac, multi
- [[methods/graph_correction]] modality: rna, atac
- [[methods/deep_generative_embedding]] modality: rna, multi
