---
type: task
id: atac_clustering
modality: atac
label: ATAC Clustering
eval_weights:
  ari: 0.35
  nmi: 0.35
  silhouette: 0.30
---
Groups cells from a scATAC-seq dataset into clusters based on chromatin accessibility profiles. Produces cluster labels and a UMAP visualization.

ATAC clustering uses spectral embedding (TF-IDF + SVD) rather than PCA. The tile matrix (500 bp bins) or consensus peak matrix can be used as input; tile matrix is preferred for initial clustering.

Stages (in order):
- [[stages/qc]] [includes]
- [[stages/peak_calling]] [includes]
- [[stages/feature_selection]] [includes]
- [[stages/embed]] [includes]
- [[stages/cluster]] [includes]
- [[stages/project]] [includes]

Evaluated by:
- [[tools/eval_clustering_metrics]] [evaluated_by]

Key decisions for the consultant:
- Peak calling (MACS3) should be run first if raw fragments are available and no peak matrix exists
- Feature selection: top 50,000 variable peaks for large datasets; fewer for small
- Spectral component 1 captures depth variation — always exclude it: use components 2–N
- If `batch_key` is present: add batch_integration stage; Harmony on spectral embedding is the default
- Resolution for Leiden: same guidance as RNA (0.5 for broad cell types, 1.0 for subtypes)
