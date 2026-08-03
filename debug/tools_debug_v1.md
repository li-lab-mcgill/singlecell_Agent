# Tools Debug Report — v1

Test inputs: `data/pbmc_RNA_count.h5ad` (9631 cells × 29095 genes) and `data/pbmc_ATAC_count.h5ad` (9631 cells × 107194 peaks).

---

## Packages Installed (Missing from venv)

| Package | Reason Needed |
|---------|--------------|
| `leidenalg` | Leiden clustering (rna/atac_cluster_leiden) |
| `louvain` | Louvain clustering (rna/atac_cluster_louvain) |
| `scikit-misc` | Seurat v3 HVG LOESS fitting |
| `scikit-image` | Scrublet threshold detection |
| `bbknn` | BBKNN batch integration |
| `scanorama` | Scanorama batch integration |
| `snapatac2` | ATAC QC, LSI, peak selection |
| `mofapy2` | MOFA+ multi-omic factor analysis |

---

## Bugs Found and Fixed

### 1. R Script Path Wrong — `parents[4]` → `parents[3]`

**Affected files:**
- `backend/tools/rna/normalize/scran.py`
- `backend/tools/rna/embed/seurat_pca.py`
- `backend/tools/rna/de/mast.py`
- `backend/tools/rna/de/deseq2.py`
- `backend/tools/rna/de/edger.py`

**Error:** `FileNotFoundError` — R script path resolved to wrong directory.

**Cause:** Tools under `backend/tools/rna/*/` used `Path(__file__).parents[4]` to reach the project root, but `parents[3]` is correct for files 4 levels deep.

**Fix:** Changed `parents[4]` to `parents[3]` in all affected `_R_SCRIPT` path definitions.

---

### 2. renv Conflict — Added `--no-init-file` to All Rscript Calls

**Affected files:**
- `backend/tools/rna/normalize/scran.py`
- `backend/tools/rna/embed/seurat_pca.py`
- `backend/tools/rna/de/mast.py`
- `backend/tools/rna/de/deseq2.py`
- `backend/tools/rna/de/edger.py`

**Error:** `Error: failed to resolve remote` — renv tried to restore packages on startup.

**Cause:** Project has an out-of-sync `renv.lock`. Without `--no-init-file`, Rscript loads `.Rprofile` which activates renv, which then fails.

**Fix:** Added `--no-init-file` flag to all `subprocess.run(["Rscript", ...])` calls (except `--version` check which doesn't load the profile).

---

### 3. OpenMP Crash on macOS — `KMP_DUPLICATE_LIB_OK`

**Affected files:**
- `backend/tools/rna/embed/seurat_pca.py`
- `backend/tools/rna/de/mast.py`
- `backend/tools/rna/de/deseq2.py`
- `backend/tools/rna/de/edger.py`

**Error:** Exit code -6 with `OMP: Error #15: Initializing libomp.dylib, but found libomp.dylib already initialized`.

**Cause:** macOS links multiple OpenMP runtimes (from conda + system R packages), causing a fatal conflict.

**Fix:** Pass `env = {**os.environ, "KMP_DUPLICATE_LIB_OK": "TRUE", "OMP_NUM_THREADS": "1"}` to `subprocess.run()`.

---

### 4. R `%in%` Fails on Reticulate Python List

**Affected files:**
- `backend/r_scripts/rna/dimreduction_seurat_pca.R` (line 60)
- `backend/r_scripts/rna/differential_expression_mast.R` (line 61)
- `backend/r_scripts/rna/differential_expression_deseq2_pseudobulk.R` (line 61)
- `backend/r_scripts/rna/differential_expression_edger_pseudobulk.R` (line 61)

**Error:** `Error in match(x, table, nomatch = 0L) : 'match' requires vector arguments`.

**Cause:** `reticulate::py_to_r(ad$layers$keys())` returns a Python list object; R's `%in%` operator requires an R character vector.

**Fix:** Wrapped with `as.character()`:
```r
# Before:
"counts" %in% reticulate::py_to_r(ad$layers$keys())
# After:
"counts" %in% as.character(reticulate::py_to_r(ad$layers$keys()))
```

---

### 5. MAST: Sparse Matrix Passed to `FromMatrix`

**Affected file:** `backend/r_scripts/rna/differential_expression_mast.R` (line 135)

**Error:** `exprsArray must be matrix, 3-D array, list or SimpleList`.

**Cause:** `log_expr` computed via sparse matrix arithmetic remains sparse; `MAST::FromMatrix` requires a dense matrix.

**Fix:** Converted to dense:
```r
# Before:
log_expr <- log1p(t(t(counts_sub) / lib_size * 1e6))
# After:
log_expr <- as.matrix(log1p(t(t(as.matrix(counts_sub)) / lib_size * 1e6)))
```

---

### 6. Scanorama: `return_dimred` Not a Valid Argument

**Affected file:** `backend/tools/rna/batch_integration/scanorama.py`

**Error:** `TypeError: integrate() got an unexpected keyword argument 'return_dimred'`.

**Cause:** scanorama API changed — `integrate_scanpy()` no longer accepts `return_dimred`.

**Fix:** Removed `return_dimred=True` from the `integrate_scanpy()` call.

---

### 7. decoupler v2 API Completely Changed

**Affected file:** `backend/tools/rna/grn/decoupler.py`

**Error:** `AttributeError: module 'decoupler' has no attribute 'get_collectri'`.

**Cause:** decoupler v2 restructured its entire API.

**Fix:**
| v1 (old) | v2 (new) |
|----------|----------|
| `dc.get_collectri(organism=..., split_complexes=False)` | `dc.op.collectri(organism=...)` |
| `dc.run_ulm(mat=adata, net=net, source=..., target=..., weight=..., use_raw=False)` | `dc.mt.ulm(data=adata, net=net, tmin=min_n, raw=False, verbose=False)` |
| Results in `adata.obsm["ulm_estimate"]` | Results in `adata.obsm["score_ulm"]` / `"padj_ulm"` |

Added backward-compatible aliasing: `adata.obsm["ulm_estimate"] = adata.obsm["score_ulm"]`.

---

### 8. GRNBoost2: arboreto Incompatible with dask ≥ 2024

**Affected file:** `backend/tools/rna/grn/grnboost2.py`

**Error:** `TypeError: Must supply at least one delayed object`.

**Cause:** arboreto's `core.py` calls `from_delayed(delayed_meta_dfs, ...)` unconditionally even when `include_meta=False`, leaving an empty list. dask ≥ 2024 (new expression API) raises `TypeError` for empty lists instead of returning an empty DataFrame.

**Fix:** Monkey-patch `arboreto.core.from_delayed` before calling `grnboost2()` to handle empty lists gracefully:
```python
def _patch_arboreto_dask() -> None:
    import arboreto.core as _arb_core
    _orig = _arb_core.from_delayed
    def _safe_from_delayed(dfs, meta=None, **kwargs):
        if not dfs:
            import pandas as pd, dask.dataframe as dd
            col_names = list(meta.keys()) if isinstance(meta, dict) else []
            return dd.from_pandas(pd.DataFrame(columns=col_names), npartitions=1)
        return _orig(dfs, meta=meta, **kwargs)
    _arb_core.from_delayed = _safe_from_delayed
```

---

### 9. WNN: `mu.pp.neighbors()` Does Not Accept AnnData

**Affected file:** `backend/tools/multi/embed/wnn.py`

**Error:** `TypeError: neighbors() got an unexpected keyword argument 'use_rep'`.

**Cause:** `muon.pp.neighbors()` only accepts `MuData`, not `AnnData` with `use_rep`. For per-modality neighbor graphs, `scanpy.pp.neighbors()` must be used.

**Fix:** Changed per-modality neighbor computation to `sc.pp.neighbors()`, then called `mu.pp.neighbors(mdata)` for WNN fusion.

---

### 10. WNN: `sc.tl.umap()` Fails on MuData

**Affected file:** `backend/tools/multi/embed/wnn.py`

**Error:** `TypeError: unhashable type: 'dict'`.

**Cause:** `scanpy.tl.umap()` does not support `MuData` objects — it tries to hash the dict-like MuData structure.

**Fix:** Changed to `mu.tl.umap(mdata, min_dist=0.3)`.

---

### 11. MOFA+: Wrong `set_data_matrix` Format

**Affected file:** `backend/tools/multi/embed/mofa.py`

**Error:** `AssertionError: Length of views names is not the same as the number of views`.

**Cause:** mofapy2's `set_data_matrix()` expects `data[views][groups]` (outer list = views, inner list = groups). Code passed `[[rna, atac]]` (1 group with 2 views).

**Fix:**
```python
# Before (wrong — 1 group containing 2 views):
ent.set_data_matrix([[rna_matrix, atac_matrix]], ...)
# After (correct — 2 views each with 1 group):
ent.set_data_matrix([[rna_matrix], [atac_matrix]], ...)
```

---

### 12. rna_velocity_scvelo: Wrong Layer Check (Mu/Ms vs spliced/unspliced)

**Affected file:** `backend/tools/rna/velocity/scvelo.py`

**Error:** `ValueError: adata.layers['Mu'] not found` when passing raw velocyto output.

**Cause:** Tool checked for `Mu`/`Ms` layers, which are computed *by* `scv.pp.moments()` internally. The actual velocyto input layers are `spliced` and `unspliced`.

**Fix:** Changed validation check from `("Mu", "Ms")` to `("spliced", "unspliced")` and updated docstring to clarify that `Mu`/`Ms` are produced internally.

---

### 13. rna_velocity_scvelo: velocity_graph Crashes via multiprocessing.Manager

**Affected file:** `backend/tools/rna/velocity/scvelo.py`

**Error:** `EOFError` from `multiprocessing.Manager().Queue()` when `show_progress_bar=True`.

**Cause:** scVelo's `parallelize()` always creates `Manager().Queue()` when `show_progress_bar=True`, regardless of `n_jobs`. This crashes in subprocess/non-interactive environments.

**Fix:**
```python
# Before:
scv.tl.velocity_graph(adata, n_jobs=1)
# After:
scv.tl.velocity_graph(adata, n_jobs=1, show_progress_bar=False)
```

---

### 14. rna_grn_pyscenic: Wrong Module Import (`pyscenic.ctx` → `pyscenic.prune` / `pyscenic.utils`)

**Affected file:** `backend/tools/rna/grn/pyscenic.py`

**Error:** `ModuleNotFoundError: No module named 'pyscenic.ctx'`

**Cause:** Tool imported from `pyscenic.ctx` which never existed. Correct modules in pyscenic 0.12.1+ are `pyscenic.prune` and `pyscenic.utils`.

**Fix:**
```python
# Before (wrong):
from pyscenic.ctx import df2regulons, load_motif_annotations
# After (correct):
from pyscenic.prune import prune2df, df2regulons
from pyscenic.utils import modules_from_adjacencies
```

Also updated the call sequence: adjacencies → `modules_from_adjacencies(adj, expr_df)` → `prune2df(dbs, modules, motif_ann_fname)` → `df2regulons(df)`.

---

### 15. rna_grn_pyscenic: NumPy 2.x Incompatibility (`np.object` removed)

**Affected file:** pyscenic package (`pyscenic/transform.py` lines 42–44)

**Error:** `AttributeError: module 'numpy' has no attribute 'object'` — `np.object` was removed in NumPy 1.24.

**Fix:** Install from the upstream master branch which contains the fix: `pip install git+https://github.com/aertslab/pySCENIC.git`

---

### 16. rna_grn_pyscenic: macOS spawn issue + dask generator incompatibility (FIXED)

**Affected file:** `backend/tools/rna/grn/pyscenic.py`

**Errors (three combined):**
1. `RuntimeError: An attempt has been made to start a new process before the current process has finished its bootstrapping phase.`
2. `TypeError: object of type 'generator' has no len()` in `pyscenic/prune.py`
3. `TypeError: Must supply at least one delayed object` in `arboreto/core.py`

**Causes:**
1. macOS uses `spawn` by default for multiprocessing. `prune2df(client_or_address='dask_multiprocessing')` calls `.compute(scheduler='processes')` which spawns worker processes — these fail on macOS before the parent is initialized.
2. pyscenic passes a generator expression to `from_delayed()`, but dask's new expression API requires a list.
3. arboreto's same `from_delayed` empty-list bug (bug #8) also triggers here in Stage 1 (GRNBoost2).

**Fix:** Added `_patch_pyscenic_dask()` called at the start of `_run_pyscenic()`:
```python
def _patch_pyscenic_dask() -> None:
    import multiprocessing
    multiprocessing.set_start_method("fork", force=True)  # Fix 1: use fork on macOS

    import pyscenic.prune as _pyscenic_prune
    _orig = _pyscenic_prune.from_delayed
    def _safe_from_delayed(dfs, meta=None, **kwargs):
        dfs = list(dfs)  # Fix 2: generator → list
        if not dfs: return dd.from_pandas(pd.DataFrame(), npartitions=1)
        return _orig(dfs, meta=meta, **kwargs) if meta is not None else _orig(dfs, **kwargs)
    _pyscenic_prune.from_delayed = _safe_from_delayed

    import arboreto.core as _arb_core            # Fix 3: same as bug #8
    _arb_core.from_delayed = _safe_arboreto_from_delayed
```

**Result:** `rna_grn_pyscenic` now passes on macOS — n_tfs=83, n_targets=1447, n_regulons=4 on pbmc subset (300 cells × 2000 HVGs).

---

### 17. rna_grn_pyscenic_aucell: GeneSignature objects required by pyscenic.aucell

**Affected file:** `backend/tools/rna/grn/pyscenic_aucell.py`

**Error:** `AttributeError: 'str' object has no attribute 'name'` inside `pyscenic/aucell.py`

**Cause:** `pyscenic.aucell()` expects a list of `GeneSignature` objects (which have `.name` and `.gene2weight`), not a plain `{str: frozenset}` dict. The tool stored regulons as `{tf: [genes]}` in `adata.uns` and converted them to `{tf: frozenset}`, then passed the dict to `aucell()`. Iterating a dict yields its keys (strings), and strings have no `.name` attribute.

**Fix:** Reconstruct `GeneSignature` objects before calling `aucell()`:
```python
from ctxcore.genesig import GeneSignature
signatures = [
    GeneSignature(name=tf, gene2weight={g: 1.0 for g in genes})
    for tf, genes in regulons.items()
]
auc_matrix = aucell(rankings, signatures, ...)
```

---

## All Tested Tools — Pass/Fail Summary

### RNA

| Tool | Status |
|------|--------|
| `rna_qc_basic` | PASS |
| `rna_qc_scrublet` | PASS (needed `scikit-image`) |
| `rna_normalize_log1p` | PASS |
| `rna_normalize_scran` | PASS (fixed path + `--no-init-file`) |
| `rna_feature_selection_scanpy_hvg` | PASS |
| `rna_feature_selection_seurat_v3` | PASS (requires full gene space for LOESS) |
| `rna_feature_selection_cellranger` | PASS |
| `rna_embed_pca` | PASS |
| `rna_embed_seurat_pca` | PASS (fixed path, KMP env, R `as.character`) |
| `rna_embed_scvi` | PASS |
| `rna_embed_scanvi` | PASS |
| `rna_cluster_leiden` | PASS |
| `rna_cluster_louvain` | PASS |
| `rna_project_umap` | PASS |
| `rna_project_tsne` | PASS |
| `rna_de_wilcoxon` | PASS |
| `rna_de_ttest` | PASS |
| `rna_de_mast` | PASS (fixed path, KMP env, R `as.character` + `as.matrix`) |
| `rna_de_deseq2` | PASS (fixed path, KMP env, R `as.character`) |
| `rna_de_edger` | PASS (fixed path, KMP env, R `as.character`) |
| `rna_annotate_celltypist` | PASS |
| `rna_batch_integration_harmony` | PASS |
| `rna_batch_integration_bbknn` | PASS |
| `rna_batch_integration_scanorama` | PASS (fixed `return_dimred` arg) |
| `rna_grn_decoupler` | PASS (fixed decoupler v2 API) |
| `rna_grn_grnboost2` | PASS (fixed arboreto/dask incompatibility) |
| `rna_annotate_cellmarker` | PASS (refs downloads cellmarker_v2; sensible PBMC annotations) |
| `rna_grn_pyscenic` | PASS (fixed macOS spawn + dask generator + arboreto empty list; see bug 16) |
| `rna_grn_pyscenic_aucell` | PASS |

### ATAC

| Tool | Status |
|------|--------|
| `atac_qc_basic` | PASS |
| `atac_feature_selection_peaks` | PASS |
| `atac_embed_lsi` | PASS |
| `atac_cluster_leiden` | PASS |
| `atac_cluster_louvain` | PASS |
| `atac_project_umap` | PASS |
| `atac_da_wilcoxon` | PASS |
| `atac_batch_integration_harmony` | PASS |
| `atac_annotate_marker_peaks` | PASS (user must supply marker peaks dict) |
| `atac_peak_to_gene_correlation` | PASS |

### RNA Velocity

| Tool | Status |
|------|--------|
| `rna_velocity_scvelo` | PASS (fixed layer check + `show_progress_bar=False`; tested with `scv.datasets.dentategyrus()`) |

### Multi-omic

| Tool | Status |
|------|--------|
| `multi_qc_intersect` | PASS |
| `multi_embed_wnn` | PASS (fixed `mu.pp.neighbors` + `mu.tl.umap`) |
| `multi_embed_mofa` | PASS (fixed `set_data_matrix` format) |
| `multi_embed_multivi` | PASS |

### Multi-omic Velocity

| Tool | Status |
|------|--------|
| `multi_velocity_knn_smooth` | NOT TESTED (missing real paired velocyto + ATAC data) |
| `multi_velocity_recover_dynamics` | NOT TESTED (missing real paired velocyto + ATAC data) |
| `multi_velocity_downstream` | NOT TESTED (missing real paired velocyto + ATAC data) |
| `multi_velocity_aggregate_peaks` | NOT TESTED (requires Cell Ranger ARC files) |
| `multi_velocity_lrt_decoupling` | NOT TESTED (requires real data; also extremely expensive) |

### Eval

| Tool | Status |
|------|--------|
| `eval_ari_nmi` | PASS |
| `eval_silhouette` | PASS |
| `eval_ilisi_clisi` | PASS |
| `eval_kbet` | PASS |
