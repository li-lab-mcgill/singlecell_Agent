---
type: tool
id: atac_topic_pycisTopic
modality: atac
stage: topic_modeling
backend: backend/tools/atac/topic/pycisTopic.py
label: Peak Topic Modeling (pycisTopic LDA)
default: false
params:
  n_topics: 40
  n_iter: 500
  random_state: 555
  n_cpu: 4
---

Fits an LDA topic model on the ATAC peak-barcode count matrix using pycisTopic's collapsed Gibbs sampler. Produces cell × topic and peak × topic matrices that capture co-accessible regulatory programs.

**Required input format:** Peak names in `adata.var_names` must be `chr:start-end` (e.g. `chr1:10000-10500`). `adata.X` must contain raw (non-normalized, non-TF-IDF) integer counts — pycisTopic handles its own normalization internally.

## Model selection

When `n_topics` is a list (e.g. `[20, 30, 40, 50]`), all models are fitted, evaluation plots (log-likelihood, Minmo coherence, Arun density) are saved to `output_dir/topic_model_selection.pdf`, and a `ValueError` is raised so the user can inspect and choose a value. Then re-run with a single `n_topics` value. **Do not expect auto-selection** — it is unreliable.

## Memory guard

- Warns at `n_obs × n_vars > 5e8` (~50k cells × 10k peaks)
- Hard stops at `> 2e9` unless `force=True`

## Outputs stored in adata

| Key | Type | Description |
|-----|------|-------------|
| `adata.obsm["X_topic"]` | ndarray cells × topics | Cell topic mixture |
| `adata.varm["topic_peak_weights"]` | ndarray peaks × topics | Peak weight per topic |
| `adata.uns["topic_region_sets"]` | dict | `{topic_id: [peak_names]}` top 500 peaks per topic |
| `adata.uns["cistopic_object_path"]` | str | Path to pickled CistopicObject (required by multi_grn_scenicplus) |
| `adata.uns["pycisTopic_model_path"]` | str | Path to pickled best LDA model |

## Prerequisite chain

`atac_topic_pycisTopic` must be run before `multi_grn_pycistarget` and `multi_grn_scenicplus`. The CistopicObject path is stored in `adata.uns` and consumed automatically by downstream tools.

**Params:**
- `n_topics`: number of topics (int) or list of ints for model selection
- `n_iter`: Gibbs sampling iterations (default 500; increase to 1000 for stability)
- `random_state`: random seed (default 555)
- `n_cpu`: parallel workers for multi-model fitting (default 4)
- `force`: bypass memory hard stop (default False)
- `output_dir`: required for persisting CistopicObject to disk

Package: [[packages/pycisTopic]]
Stage: [[stages/topic_modeling]]
