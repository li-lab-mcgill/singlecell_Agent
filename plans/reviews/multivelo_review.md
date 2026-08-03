# MultiVelo Implementation Plan — Review

**Plan file:** `plans/multiVelo_plan.md`  
**Reviewer:** Claude (computational biology code review)

---

## Review History

| Pass | Date | Issues Found | Issues Resolved |
|---|---|---|---|
| Pass 1 | 2026-05-14 | 12 (5 critical, 4 moderate, 3 minor) | — |
| Pass 2 | 2026-05-14 | 5 new (1 critical, 3 moderate, 1 minor) | 12/12 from Pass 1 |
| Pass 3 | 2026-05-14 | 5 new (1 critical, 2 moderate, 2 minor) | 5/5 from Pass 2 |

---

## Summary

The DAG design, dual-AnnData convention, `VelocityResult`/`VelocityDownstreamResult` dataclasses, executor auto-wiring extension, and tool decomposition rationale are all well-designed. All 12 Pass 1 issues were resolved in the updated plan. Pass 2 found 5 new issues: one critical (`scv.pp.highly_variable_genes` does not exist), two moderate issues around `LRT_decoupling()` return value handling, and two housekeeping items.

---

## Pass 1 Issues — All Resolved

| # | Tool | Issue | Fix Applied |
|---|---|---|---|
| 1 | `rna_velocity_scvelo` | `n_top_genes` not a param of `filter_and_normalize()` | Split into `filter_and_normalize()` + `highly_variable_genes()` step |
| 2 | `multi_velocity_recover_dynamics` | `fit_decoupling`, `weight_c`, `n_pcs`, `n_neighbors` claimed invalid | Verified as valid from source; all restored with confirmed upstream signature |
| 3 | `multi_velocity_downstream` | `mv.velocity_graph()` claimed to have no `vkey` | `vkey` confirmed valid; correct call documented |
| 4 | `downstream` + `lrt` | `mv.LRT_decoupling()` requires two AnnData; ATAC path missing | `atac_h5ad_path` added to both signatures |
| 5 | `multi_velocity_knn_smooth` | `toarray()` produces wrong indices and risks OOM | Sparse-aware row-by-row extraction with `getrow()` documented |
| 6 | `rna_velocity_scvelo` | `moments()` ignores `obsp["connectivities"]`; prerequisite misleading | Prerequisite updated; `use_rep="X_pca"` documented; DAG note added |
| 7 | `multi_velocity_downstream` | `mv.latent_time(root_key=None)` — `root_key` unconfirmed | `vkey` confirmed; `root_key` removed; correct call documented |
| 8 | `multi_velocity_lrt` | `fit_likelihood_c` not a confirmed var column | Confirmed from source; column now appears in Tool 4 var column table |
| 9 | `multi_velocity_recover_dynamics` | `set_velocity_genes(min_r2=...)` unconfirmed param | `likelihood_lower` confirmed as correct param name; signature updated |
| 10 | `multi_velocity_recover_dynamics` | `extra_color_key`/`save_plot` are plotting concerns | Removed from tool signature; note added for future plot tool |
| 11 | `multi_velocity_downstream` | Return type `dict` inconsistent with dataclass convention | `VelocityDownstreamResult` dataclass added to `types.py` |
| 12 | `multi_velocity_knn_smooth` | `n_neighbors=None` fallback silently produces `TypeError` | Explicit `ValueError` guard added |

---

## Pass 2 Issues — All Resolved

| # | Tool | Issue | Fix Applied |
|---|---|---|---|
| 13 | `rna_velocity_scvelo` | `scv.pp.highly_variable_genes()` does not exist | HVG delegated to upstream `rna_feature_selection_scanpy_hvg`; removed from tool |
| 14 | `lrt` + `downstream` | `LRT_decoupling()` return value discarded; adata never updated | `_, _, lrt_df = mv.LRT_decoupling(...)` with `adata.uns["lrt_decoupling"]` storage |
| 15 | `multi_velocity_lrt` | `VelocityDownstreamResult` cannot be correctly populated | `LRTResult` dataclass added; return type updated |
| 16 | `multi_velocity_downstream` | `lrt_pval_threshold` removed from signature | `lrt_pval_threshold: float = 0.05` restored |
| 17 | `multi_velocity_recover_dynamics` | `n_jobs=None` semantics differ from joblib | Implementation note added clarifying MultiVelo's `None` → `os.cpu_count()` behavior |

---

## Pass 3 Issues — Open

---

### Critical

#### 1. `rna_velocity_scvelo` — `scv.pp.highly_variable_genes()` does not exist

Line 213: `scv.pp.highly_variable_genes(adata, n_top_genes=n_top_genes)` — this function is not in the scVelo package. The scVelo `pp` module only exports: `filter_and_normalize`, `filter_genes`, `moments`, `neighbors`, `normalize_per_cell`, `remove_duplicate_cells`. Calling it raises `AttributeError`.

The correct function is from scanpy, confirmed by scVelo's own test suite:

```python
import scanpy as sc
sc.pp.highly_variable_genes(adata, n_top_genes=n_top_genes)
```

Change `scv.pp.highly_variable_genes` → `sc.pp.highly_variable_genes` in Step 2 and add `import scanpy as sc` to the implementation imports.

---

### Moderate

#### 2. `multi_velocity_lrt` and `multi_velocity_downstream` — `mv.LRT_decoupling()` return value is discarded; adata never updated

Both tools call `mv.LRT_decoupling(adata, adata_atac)` without capturing the return value. The function does **not** modify either AnnData in-place — it returns three objects:

```python
adata_w_decoupled, adata_wo_decoupled, lrt_df = mv.LRT_decoupling(adata, adata_atac)
```

Where `lrt_df` is a DataFrame with columns:
`likelihood_c_w_decoupled`, `likelihood_c_wo_decoupled`, `LRT_c`, `pval_c`,
`likelihood_w_decoupled`, `likelihood_wo_decoupled`, `LRT`, `pval`

The current plan discards all three return values, meaning LRT results are silently lost. Fix for both tools:

```python
_, _, lrt_df = mv.LRT_decoupling(adata, adata_atac)

# Persist results
adata.uns["lrt_decoupling"] = lrt_df.to_dict()

# Compute counts using a p-value threshold
n_decoupled = int((lrt_df["pval_c"] < lrt_pval_threshold).sum())
n_coupled    = int((lrt_df["pval_c"] >= lrt_pval_threshold).sum())

# Optionally save table
if output_dir:
    lrt_df.to_parquet(output_dir / "lrt_decoupling.parquet")
```

Also update the `multi_velocity_downstream` note at Step 4 which incorrectly states that `LRT_decoupling()` "updates `adata.var['fit_model']` in-place" — this is wrong.

---

#### 3. `multi_velocity_lrt` — `VelocityDownstreamResult` cannot be correctly populated

`VelocityDownstreamResult` has two required fields without defaults: `velocity_key: str` and `n_velocity_genes_graph: int`. The LRT tool does not compute either — it only produces decoupling statistics. Forcing it to return `VelocityDownstreamResult` requires fabricating values for these fields.

Define a dedicated `LRTResult` dataclass instead:

```python
@dataclass
class LRTResult:
    """Result of epigenome–transcriptome decoupling LRT (mv.LRT_decoupling)."""
    n_genes_tested: int
    n_decoupled: int       # genes where chromatin opens before transcription (Model 2)
    n_coupled: int         # genes where chromatin and transcription are coupled (Model 1)
    pct_decoupled: float
    lrt_table_path: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]: ...
```

Update `multi_velocity_lrt` return type to `LRTResult` and add `LRTResult` to the `types.py` addition list in Section 7.

---

#### 4. `multi_velocity_downstream` — `lrt_pval_threshold` removed from signature but needed for `n_decoupled` computation

The updated `multi_velocity_downstream` signature (line 506–517) dropped the `lrt_threshold` parameter. However, computing `n_decoupled` / `n_coupled` from the `lrt_df` returned by `LRT_decoupling()` requires a p-value cutoff. Without it, the counts cannot be computed and `VelocityDownstreamResult.lrt_n_decoupled` will always be `None`.

Add it back to the signature:

```python
def run(
    adata,
    *,
    atac_h5ad_path: str | Path | None = None,
    velocity_key: str | None = None,
    embedding_key: str = "X_umap",
    compute_latent_time: bool = True,
    run_lrt: bool = False,
    lrt_pval_threshold: float = 0.05,    # ADD — p-value cutoff for decoupled/coupled classification
    output_dir: Path | None = None,
) -> VelocityDownstreamResult:
```

---

### Minor

#### 5. `multi_velocity_recover_dynamics` — `n_jobs=None` semantics differ from joblib; add implementation note

Verified from MultiVelo source: `n_jobs=None` → `os.cpu_count()` (all CPUs). This differs from joblib's convention where `None` means 1 CPU and `-1` means all CPUs. The plan's default `n_jobs: int | None = None` is correct, but add a note in the implementation so developers do not accidentally "fix" it:

```python
# MultiVelo note: n_jobs=None → os.cpu_count() (all CPUs).
# This differs from joblib: do NOT change to n_jobs=-1 expecting "all CPUs" behavior.
# Both None and -1 result in os.cpu_count() in MultiVelo's internal guard, but None is preferred.
```

---

## Pass 3 Issues — Open

---

### Critical

#### 1. `rna_velocity_scvelo` — `use_rep="X_pca"` unconditional; raises `KeyError` when X_pca absent

Line 246: `scv.pp.moments(adata, n_pcs=n_pcs, n_neighbors=n_neighbors, use_rep="X_pca")` is called unconditionally. Verified from scVelo source: if `adata.obsm["X_pca"]` does not exist, the lookup `adata.obsm[use_rep]` raises `KeyError` with no fallback.

The plan says X_pca is "recommended but not required," which directly contradicts the unconditional call. Fix:

```python
use_rep = "X_pca" if "X_pca" in adata.obsm else None
scv.pp.moments(adata, n_pcs=n_pcs, n_neighbors=n_neighbors, use_rep=use_rep)
```

---

### Moderate

#### 2. `multi_velocity_knn_smooth` — `adata.uns["velocity_preprocess"]["knn_smooth"] = True` raises `KeyError` when `aggregate_peaks` was skipped

Step 6: if the user provides pre-existing gene-level ATAC data (e.g., ArchR gene scores) and skips `multi_velocity_aggregate_peaks`, `adata.uns["velocity_preprocess"]` does not exist. The assignment raises `KeyError`. Fix:

```python
adata.uns.setdefault("velocity_preprocess", {})["knn_smooth"] = True
```

---

#### 3. `multi_velocity_downstream` — `n_velocity_genes_graph` source undocumented; return statement absent

The plan ends Step 5 with "Return `VelocityDownstreamResult`" but never shows how the dataclass is constructed. `VelocityDownstreamResult` has two required no-default fields — `velocity_key: str` and `n_velocity_genes_graph: int` — and neither has a documented source in the steps. Without this, implementations will fail with `TypeError`.

Add to implementation notes:

```python
# n_velocity_genes_graph: use velo_s_genes flag computed by set_velocity_genes in recover_dynamics
n_velocity_genes_graph = int(adata.var.get("velo_s_genes", pd.Series(dtype=bool)).sum())

return VelocityDownstreamResult(
    velocity_key=vkey,
    n_velocity_genes_graph=n_velocity_genes_graph,
    latent_time_key="latent_time" if compute_latent_time else None,
    lrt_n_decoupled=n_decoupled if run_lrt else None,
    lrt_n_coupled=n_coupled if run_lrt else None,
    metadata={"lrt_pval_threshold": lrt_pval_threshold if run_lrt else None},
)
```

---

### Minor

#### 4. `rna_velocity_scvelo` — no runtime warning when `highly_variable` column absent

The plan delegates HVG to an upstream tool but `rna_velocity_scvelo` never checks this at runtime. If the user skips the upstream HVG step, `moments()` runs silently on all genes (verified: `use_highly_variable=True` is the default but only affects internal PCA, not gene subsetting for moment computation). Add a soft warning:

```python
if "highly_variable" not in adata.var:
    import warnings
    warnings.warn(
        "adata.var['highly_variable'] not found. Run rna_feature_selection_scanpy_hvg "
        "first for best results. Continuing with all genes.",
        UserWarning,
    )
```

---

#### 5. `rna_velocity_scvelo` — `moments()` does not subset genes by HVG flags; plan ambiguous on intent

Verified from source: `scv.pp.moments(use_highly_variable=True)` (the default) only restricts genes during internal PCA computation — it does **not** filter the moment calculation to HVGs. Pre-computed `adata.var["highly_variable"]` from the upstream tool is therefore not used to restrict velocity fitting to HVG genes.

The plan is ambiguous: it says HVG is done upstream and "do not re-run HVG inside this tool," but does not document whether velocity is fitted on all genes or only HVGs. Clarify explicitly in the implementation notes. If the intent is to fit velocity only on HVGs, add a pre-filter step; otherwise document that all genes are used for moment computation regardless.

---

## Full Issue Tracker

| # | Pass | Severity | Tool | Issue | Status |
|---|---|---|---|---|---|
| 1 | 1 | Critical | `rna_velocity_scvelo` | `n_top_genes` not a param of `filter_and_normalize()` | ✅ |
| 2 | 1 | Critical | `multi_velocity_recover_dynamics` | `fit_decoupling`, `weight_c`, `n_pcs`, `n_neighbors` claimed invalid | ✅ |
| 3 | 1 | Critical | `multi_velocity_downstream` | `mv.velocity_graph()` `vkey` claimed invalid | ✅ |
| 4 | 1 | Critical | `downstream` + `lrt` | `LRT_decoupling()` ATAC arg missing | ✅ |
| 5 | 1 | Critical | `multi_velocity_knn_smooth` | `toarray()` wrong indices + OOM risk | ✅ |
| 6 | 1 | Moderate | `rna_velocity_scvelo` | `moments()` ignores `obsp`; misleading prerequisite | ✅ |
| 7 | 1 | Moderate | `multi_velocity_downstream` | `root_key` unconfirmed param on `latent_time()` | ✅ |
| 8 | 1 | Moderate | `multi_velocity_lrt` | `fit_likelihood_c` unconfirmed var column | ✅ |
| 9 | 1 | Moderate | `multi_velocity_recover_dynamics` | `min_r2` wrong param name for `set_velocity_genes()` | ✅ |
| 10 | 1 | Minor | `multi_velocity_recover_dynamics` | `extra_color_key`/`save_plot` plotting concerns in fitting tool | ✅ |
| 11 | 1 | Minor | `multi_velocity_downstream` | Return type `dict` inconsistent with dataclass convention | ✅ |
| 12 | 1 | Minor | `multi_velocity_knn_smooth` | `n_neighbors=None` silent `TypeError` | ✅ |
| 13 | 2 | Critical | `rna_velocity_scvelo` | `scv.pp.highly_variable_genes()` does not exist | ✅ |
| 14 | 2 | Moderate | `lrt` + `downstream` | `LRT_decoupling()` return value discarded; adata never updated | ✅ |
| 15 | 2 | Moderate | `multi_velocity_lrt` | Wrong return type; needs `LRTResult` dataclass | ✅ |
| 16 | 2 | Moderate | `multi_velocity_downstream` | `lrt_pval_threshold` removed from signature | ✅ |
| 17 | 2 | Minor | `multi_velocity_recover_dynamics` | `n_jobs=None` semantics note missing | ✅ |
| 18 | 3 | **Critical** | `rna_velocity_scvelo` | `use_rep="X_pca"` unconditional → `KeyError` when X_pca absent | ⚠️ Open |
| 19 | 3 | Moderate | `multi_velocity_knn_smooth` | `velocity_preprocess` key absent → `KeyError` when `aggregate_peaks` skipped | ⚠️ Open |
| 20 | 3 | Moderate | `multi_velocity_downstream` | `n_velocity_genes_graph` source undocumented; return statement absent | ⚠️ Open |
| 21 | 3 | Minor | `rna_velocity_scvelo` | No runtime warning when `highly_variable` column absent | ⚠️ Open |
| 22 | 3 | Minor | `rna_velocity_scvelo` | `moments()` does not subset genes by HVG flags; plan ambiguous on intent | ⚠️ Open |
