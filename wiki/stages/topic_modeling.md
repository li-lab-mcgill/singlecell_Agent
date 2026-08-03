---
type: stage
id: topic_modeling
label: Topic Modeling
---

The topic modeling stage decomposes a peak-barcode or gene-barcode count matrix into latent topics using dimensionality reduction methods such as Latent Dirichlet Allocation (LDA). Each topic represents a co-accessible or co-expressed regulatory program; cells are modeled as mixtures over topics.

In the SCENIC+ pipeline, topic modeling on the ATAC peak matrix is a required preprocessing step before TF-region motif enrichment. The resulting topic region sets (top peaks per topic) serve as the region inputs to pycistarget.

## Model selection

When fitting multiple topic counts, always inspect the evaluation plots before proceeding:
- **Log-likelihood**: should plateau; increasing n_topics beyond the plateau gives diminishing returns
- **Minmo coherence** (higher = better): measures semantic coherence of top-ranked regions per topic
- **Arun density** (lower = better): measures how well topics occupy the data manifold

Re-run with a single `n_topics` value after inspection. Automatic selection is not recommended.

## Output

- Cell × topic matrix → `adata.obsm["X_topic"]`
- Peak × topic weight matrix → `adata.varm["topic_peak_weights"]`
- Topic region sets → `adata.uns["topic_region_sets"]`
- Serialized CistopicObject → `adata.uns["cistopic_object_path"]`
- Path to best LDA model pickle → `adata.uns["pycisTopic_model_path"]`

Edges:
- [[tools/atac_topic_pycisTopic]] implements
