---
type: method
id: joint_embedding
label: Joint Multi-omic Embedding
---

Joint embedding methods compute a unified low-dimensional representation of cells from multiple modalities simultaneously. Rather than integrating modalities post-hoc, these methods learn a shared latent space that captures information from both RNA and ATAC.

Two primary approaches:

**MultiVI (scvi-tools)**: extends scVI to paired RNA+ATAC data. Models RNA counts as negative binomial and ATAC accessibility as Bernoulli. Produces a joint latent space `adata.obsm["X_multivi"]`. Handles batch correction via `batch_key`. Best for 10x Multiome data.

**WNN (Weighted Nearest Neighbors)**: computes per-modality KNN graphs then learns cell-specific weights reflecting each modality's informativeness. Implemented in muon (`muon.pp.neighbors()`). Does not produce a single embedding but a weighted graph used for clustering and UMAP. More flexible — works with any modality combination.

**MOFA+**: matrix factorization across modalities; produces shared factors in `adata.obsm["X_mofa"]`. Better for discovery (what varies across modalities?) than for visualization.

For clustering and UMAP from 10x Multiome, MultiVI or WNN is recommended. For understanding shared and modality-specific variation, MOFA+ is more informative.

Edges:
- [[tools/multi_embed_multivi]] implements
- [[tools/multi_embed_wnn]] implements
