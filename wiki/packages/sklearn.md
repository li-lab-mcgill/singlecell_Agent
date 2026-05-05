---
type: package
id: sklearn
version: ">=1.3"
citation: Pedregosa et al. 2011 JMLR
---

scikit-learn provides general-purpose machine learning utilities used throughout the pipeline for metrics, dimensionality reduction, and model evaluation.

Install: `pip install scikit-learn`

Key functions used in single-cell analysis:

- `sklearn.metrics.adjusted_rand_score` — ARI for clustering evaluation against a ground-truth label
- `sklearn.metrics.normalized_mutual_info_score` — NMI for clustering evaluation
- `sklearn.metrics.silhouette_score` — silhouette coefficient for unsupervised cluster quality
- `sklearn.decomposition.PCA` — fallback PCA when scanpy's implementation is insufficient
- `sklearn.preprocessing.LabelEncoder` — integer encoding of categorical cell labels
- `sklearn.model_selection.StratifiedKFold` — stratified cross-validation for classifier evaluation

For clustering metrics, always call `adjusted_rand_score(labels_true, labels_pred)`. Both arguments must be 1-D arrays of the same length. NMI is symmetric; ARI handles imbalanced clusters better.

Silhouette score requires a distance or embedding matrix — pass `adata.obsm["X_pca"]` or the corrected embedding, not raw counts.
