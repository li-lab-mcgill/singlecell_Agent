# SCENIC+ Implementation Plan — Review

**Plan file:** `plans/scenicplus_implementation.md`  
**Reviewer:** Claude (computational biology code review)

---

## Review History

| Pass | Date | Issues Found | Issues Resolved |
|---|---|---|---|
| Pass 1 | 2026-05-13 | 12 (5 critical, 4 moderate, 3 minor) | — |
| Pass 2 | 2026-05-13 | 5 new (3 critical, 1 moderate, 1 minor) | 12/12 from Pass 1 |

---

## Summary

The dependency graph, reuse assessment, `eGRN` type, resource-sharing rationale, and implementation order are sound. All 12 issues from Pass 1 were resolved in the revised plan. Pass 2 identified 5 new issues from deeper API verification: two missing parameters in `multi_grn_pycistarget`, the wrong SCENIC+ object constructor in `multi_grn_scenicplus`, a missing `CistopicObject` construction step in `atac_topic_pycisTopic`, and an undocumented model-selection strategy.

---

## Pass 1 Issues — All Resolved

The following were identified in Pass 1 and correctly fixed in the revised plan:

| # | Tool | Issue | Fix Applied |
|---|---|---|---|
| 1 | `multi_grn_pycistarget` | PyRanges conversion step missing | `_peaks_to_pyranges()` helper added |
| 2 | `multi_grn_pycistarget` | Wrong `auc/nes/rank_threshold` names; `rank_threshold` was int | Renamed to `ctx_*`; typed as float fraction |
| 3 | `multi_grn_scenicplus` | Wrong function name `infer_eRegulons()`; no object construction | `build_grn()` / `infer_regulons()` + `SCENICPLUS` object pattern added |
| 4 | `multi_grn_peak_to_gene` | Single `importance_threshold` conflated two params; wrong module | Separated into `importance_threshold` + `rho_threshold`; module path fixed |
| 5 | Tools 4 & 5 | `run_aucell` and `celltype_key` absent from signatures | Both added |
| 6 | `atac_topic_pycisTopic` | Wrong matrix attribute names; missing `tmp_path` | `model.cell_topic` / `model.topic_region.T` noted; `tmp_path` added |
| 7 | `multi_grn_pycistarget` | DEM background unspecified | `adata.var_names` as background documented |
| 8 | `multi_grn_scenicplus` | `rho_threshold` params for activating/repressing split absent | `rho_tf_gene_threshold` / `rho_region_gene_threshold` added |
| 9 | `atac_topic_pycisTopic` | Memory guard at 5e9 was 10× too high | Guards set at warn=5e8, hard stop=2e9 with `force` override |
| 10 | `rna_grn_pyscenic_aucell` | `.obsm` cannot store DataFrames | `.values` extraction + `.uns` column names documented |
| 11 | `multi_grn_peak_to_gene` | `biomart_host` repurposed for GTF path | `gtf_path` added as proper parameter |
| 12 | Tools 4 & 5 | Key collision on re-scoring undocumented | Overwrite behavior documented in both tools |

---

## Pass 2 Issues — Open

---

### Critical

#### 1. `multi_grn_pycistarget` — `species` and `annotation_version` missing from signature

`run_pycistarget()` requires both. Without `species`, motif annotation lookup fails silently or uses wrong organism mappings:

```python
def run(
    adata,
    *,
    tf_list_path: str | Path,
    cistarget_db_paths: list[str | Path] | str | Path,
    motif_annotations_path: str | Path,
    species: str,                              # ADD — 'homo_sapiens', 'mus_musculus', 'drosophila_melanogaster'
    annotation_version: str = "v10nr_clust",   # ADD — must match the downloaded feather database version
    region_sets_key: str = "topic_region_sets",
    fraction_overlap: float = 0.4,
    ctx_auc_threshold: float = 0.005,
    ctx_nes_threshold: float = 3.0,
    ctx_rank_threshold: float = 0.05,
    n_cpu: int = 4,
    output_dir: Path | None = None,
) -> object:
```

`species` must also appear in the wiki frontmatter params (no default — user must specify). The `annotation_version` default `"v10nr_clust"` must be verified against the version of feather files bundled in the existing `pyscenic_databases` resource node — add a cross-reference note if they differ.

---

#### 2. `atac_topic_pycisTopic` — `CistopicObject` construction step missing; matrix must be transposed

The plan describes extracting `model.cell_topic` and `model.topic_region` but never shows how to construct the `CistopicObject` from `adata`. This is non-trivial and has an orientation trap:

- `adata.X` is **cells × peaks** (AnnData convention, cells as rows)
- `create_cistopic_object()` requires **regions × cells** (`fragment_matrix` parameter, regions as rows)

Add to the implementation notes before the model-fitting step:

```python
from pycisTopic.cistopic_class import create_cistopic_object

# adata.X is cells × peaks; CistopicObject requires regions × cells
fragment_matrix = adata.X.T  # transpose; use .tocsr() if sparse

cisTopic_obj = create_cistopic_object(
    fragment_matrix=fragment_matrix,
    cell_names=list(adata.obs_names),
    region_names=list(adata.var_names),  # must be 'chr:start-end' format
)
```

Also add an assertion that peak names are in `chr:start-end` format (pycisTopic parses coordinates from these strings and will silently produce wrong regions otherwise):

```python
assert all(":" in v and "-" in v for v in adata.var_names[:5]), (
    "Peak names must be in 'chr:start-end' format for pycisTopic"
)
```

---

#### 3. `multi_grn_scenicplus` — Use `create_SCENICPLUS_object()`, not the raw `SCENICPLUS()` constructor

The current plan uses `SCENICPLUS(ACC_mat=adata.X, EXP_mat=rna_adata.X, ...)`. SCENIC+ v1.0's public API is `create_SCENICPLUS_object()`, which handles cell barcode alignment between RNA and ATAC, validates the `menr` nested-dict structure, and sets up internal index mappings. Bypassing it risks silent cell misalignment:

```python
from scenicplus.scenicplus_class import create_SCENICPLUS_object

scplus_obj = create_SCENICPLUS_object(
    GEX_anndata=rna_adata,          # AnnData cells × genes
    ACC_anndata=adata,              # AnnData cells × peaks
    cistarget_result=pycistarget_result,   # loaded from pycistarget_result_path pickle
    multi_ome_mode=True,            # True = paired RNA+ATAC (same cells); False = unpaired
)
```

`multi_ome_mode=True` is required for paired scRNA+scATAC data where cells are shared across modalities. The serialized pickle from Tool 2 loads directly into `cistarget_result=` — the existing serialization approach is correct, only the call site changes.

Replace all references to `SCENICPLUS()` constructor in Tool 4 with `create_SCENICPLUS_object()`.

---

### Moderate

#### 4. `atac_topic_pycisTopic` — Automatic model selection strategy is unreliable in a pipeline context

The plan states: "when a list is given, run all models and select the best by coherence score." pycisTopic's `evaluate_models()` automatic selection is acknowledged by the authors as suboptimal — it tends to select the highest topic count where all metrics are simultaneously maximized, which is biologically uninformative.

In a non-interactive pipeline, this needs a deterministic policy. **Recommended approach:**

When `n_topics` is a list:
1. Fit all models.
2. Save all models to `output_dir / "topic_models/"`.
3. Save evaluation plots (log-likelihood, Minmo coherence, Arun_2010 density) to `output_dir / "topic_model_selection.pdf"`.
4. **Do not auto-select.** Raise an informative error:
   ```
   ValueError: Multiple topic models fitted. Inspect output_dir/topic_model_selection.pdf
   and re-run with n_topics=<chosen_value> to proceed.
   ```

This is safer than silent auto-selection. Add a note to the wiki that model selection requires human inspection when a list is passed.

---

### Minor

#### 5. `multi_grn_peak_to_gene` — `correlation_scoring_method` not passed explicitly in code snippet

The underlying function `calculate_regions_to_genes_relationships()` uses parameter `correlation_scoring_method` (values: `'SR'` = Spearman, `'PR'` = Pearson). The plan's code snippet omits it, relying on the default. Since Spearman is correct for SCENIC+ and the plan explicitly chooses it, pass it explicitly to guard against version differences in default behavior:

```python
r2g_df = calculate_regions_to_genes_relationships(
    search_space=search_space_df,
    atac_adata=adata,
    rna_adata=rna_adata,
    importance_threshold=importance_threshold,
    rho_threshold=rho_threshold,
    correlation_scoring_method="SR",    # ADD — 'SR'=Spearman (default), 'PR'=Pearson
    n_cpu=n_cpu,
)
```

---

## Full Issue Tracker

| # | Pass | Severity | Tool | Issue | Status |
|---|---|---|---|---|---|
| 1 | 1 | Critical | `multi_grn_pycistarget` | PyRanges conversion missing | ✅ Resolved |
| 2 | 1 | Critical | `multi_grn_pycistarget` | Wrong `ctx_*` param names; `rank_threshold` wrong type | ✅ Resolved |
| 3 | 1 | Critical | `multi_grn_scenicplus` | Wrong function name; no SCENICPLUS object | ✅ Resolved |
| 4 | 1 | Critical | `multi_grn_peak_to_gene` | `importance_threshold` conflated; wrong module path | ✅ Resolved |
| 5 | 1 | Critical | Tools 4 & 5 | `run_aucell`, `celltype_key` missing from signatures | ✅ Resolved |
| 6 | 1 | Moderate | `atac_topic_pycisTopic` | Wrong matrix attributes; missing `tmp_path` | ✅ Resolved |
| 7 | 1 | Moderate | `multi_grn_pycistarget` | DEM background unspecified | ✅ Resolved |
| 8 | 1 | Moderate | `multi_grn_scenicplus` | `rho_threshold` params missing | ✅ Resolved |
| 9 | 1 | Moderate | `atac_topic_pycisTopic` | Memory guard threshold 10× too high | ✅ Resolved |
| 10 | 1 | Minor | `rna_grn_pyscenic_aucell` | `.obsm` cannot store DataFrames | ✅ Resolved |
| 11 | 1 | Minor | `multi_grn_peak_to_gene` | `biomart_host` repurposing deferred | ✅ Resolved |
| 12 | 1 | Minor | Tools 4 & 5 | Key collision on re-scoring undocumented | ✅ Resolved |
| 13 | 2 | Critical | `multi_grn_pycistarget` | `species` and `annotation_version` missing from signature | ⚠️ Open |
| 14 | 2 | Critical | `atac_topic_pycisTopic` | `CistopicObject` construction missing; `adata.X` must be transposed | ⚠️ Open |
| 15 | 2 | Critical | `multi_grn_scenicplus` | Raw `SCENICPLUS()` constructor; use `create_SCENICPLUS_object()` + `multi_ome_mode=True` | ⚠️ Open |
| 16 | 2 | Moderate | `atac_topic_pycisTopic` | Auto model selection unreliable; no deterministic pipeline strategy | ⚠️ Open |
| 17 | 2 | Minor | `multi_grn_peak_to_gene` | `correlation_scoring_method="SR"` not explicit in code snippet | ⚠️ Open |
