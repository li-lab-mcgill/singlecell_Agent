---
type: package
id: scanpy
version: ">=1.9"
citation: Wolf et al. 2018, Genome Biology
---

Scanpy is the primary Python framework for single-cell RNA-seq analysis built on AnnData. It provides tools for preprocessing, visualization, clustering, trajectory inference, and differential expression. Most RNA pipeline stages have at least one scanpy-based tool.

Install: `pip install scanpy`

Key capabilities used in this wiki:
- `sc.pp.*` — preprocessing (normalize, filter, PCA, neighbors)
- `sc.tl.leiden` / `sc.tl.louvain` — graph clustering
- `sc.tl.umap` / `sc.tl.tsne` — 2D projection
- `sc.tl.rank_genes_groups` — differential expression (wilcoxon, t-test, logreg)
- `sc.external.pp.scrublet` — doublet detection wrapper

AnnData stores results in `adata.obsm` (embeddings), `adata.obs` (cell metadata), `adata.uns` (unstructured metadata).
