---
type: tool
id: eval_ari_nmi
stage: eval
modality: rna, atac, multi
backend: backend/tools/eval/ari_nmi.py
---

Computes ARI (Adjusted Rand Index) and NMI (Normalized Mutual Information) between predicted cluster labels and ground-truth cell type labels.

Key parameters:
- `cluster_key` (required): `adata.obs` column with predicted cluster labels
- `label_key` (required): `adata.obs` column with ground-truth labels
- `result_key` (default "clustering_eval"): `adata.uns` key for storing results

Returns and stores:
- `ari`: Adjusted Rand Index; range [-1, 1]; 1 = perfect agreement, 0 = random
- `nmi`: Normalized Mutual Information; range [0, 1]; 1 = perfect agreement

Both metrics are robust to cluster label permutation and cluster count differences. ARI handles imbalanced cluster sizes better than NMI.

Package: [[packages/sklearn]]
Method: [[methods/clustering_metrics]]
