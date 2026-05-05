---
type: task
id: rna_clustering
modality: rna
label: RNA Clustering
eval_weights:
  ari: 0.35
  nmi: 0.35
  silhouette: 0.30
---
Groups cells from a scRNA-seq dataset into clusters representing distinct cell types or cell states. The pipeline produces a cluster label per cell, a UMAP for visualization, and clustering quality metrics.

This task is the foundational first step in most scRNA-seq analyses. Clusters from this task are used as input for annotation, DE, and DA tasks.

Stages (in order):
- [[stages/qc]] [includes]
- [[stages/normalize]] [includes]
- [[stages/feature_selection]] [includes]
- [[stages/embed]] [includes]
- [[stages/cluster]] [includes]
- [[stages/project]] [includes]

Evaluated by:
- [[tools/eval_ari_nmi]] [evaluated_by]

Key decisions for the consultant:
- If `batch_key` is provided: add batch_integration stage after embed; choose Harmony (default) or BBKNN or scVI (if batch effects are strong)
- Resolution parameter for Leiden: default 0.5 for broad cell types; user can override
- Number of PCA components: default 30; reduce to 15 for small datasets (<5000 cells)
- If no ground-truth labels: ARI/NMI cannot be computed; only silhouette score is reported
