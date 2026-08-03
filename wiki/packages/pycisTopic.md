---
type: package
id: pycisTopic
version: ">=1.0"
citation: Bravo González-Blas et al. 2023 Nature Methods (SCENIC+)
---

pycisTopic implements Latent Dirichlet Allocation (LDA) topic modeling on ATAC-seq peak-barcode count matrices. It decomposes the chromatin accessibility landscape into latent "topics" that capture co-accessible regulatory programs across cells.

Install from source:

```bash
git clone https://github.com/aertslab/pycisTopic.git
cd pycisTopic
pip install -e .
```

Do not assume `pip install pycisTopic` is available or sufficient in the runtime environment. For reproducible agent execution, install pycisTopic into the same Python environment or container image used by the backend tool runner.

## Core concepts

- **Topics**: Each topic is a probability distribution over genomic regions. Cells are represented as mixtures of topics.
- **CistopicObject**: The main data container; stores the peak × cell count matrix, model outputs, and downstream annotations.
- **Topic region sets**: Top peaks per topic; used as input to cisTarget motif enrichment.

## Key functions

- `create_cistopic_object(fragment_matrix, cell_names, region_names)` — requires a **regions × cells** matrix (transposed from AnnData convention)
- `run_cgs_models(cisTopic_obj, n_topics, n_cpu, n_iter, ...)` — collapsed Gibbs sampler; **`n_topics` must always be `list[int]`**, never a bare `int` — passing a bare int will fail or produce wrong results. Always wrap: `n_topics=[40]` not `n_topics=40`.
- `evaluate_models(models, ...)` — produces log-likelihood / coherence plots for model selection

## Model selection

When multiple `n_topics` values are provided, pycisTopic fits all models and saves evaluation plots. Automatic selection is unreliable — **always inspect the plots** (log-likelihood stabilization, Minmo coherence, Arun density) and re-run with a single chosen value.

## Output attributes

After fitting, the selected model exposes:
- `model.cell_topic` — cell × topic matrix (correct orientation, ready for `adata.obsm`)
- `model.topic_region` — **topic × peak** matrix (must be transposed to get peak × topic for `adata.varm`)

## Temp files and output paths

`run_cgs_models()` writes large Gibbs sampling temporary files during sampling. Use `save_path=str(output_dir / "topic_models")` to enable per-model saving to disk as they complete — this avoids holding all models in memory simultaneously. Use the `_temp_dir` parameter to redirect sampling scratch files away from `/tmp`, which can fill quickly on large datasets (each model iteration can write several GB).

## Memory considerations

LDA loads the full peak × cell matrix into memory. For 50k cells × 200k peaks this can exceed 100 GB. Subset to highly variable peaks first, or run on a cluster with adequate RAM.

Used by: [[tools/atac_topic_pycisTopic]]
