# SCENIC+ Wiki Code Review

**Reviewed**: 2026-05-14  
**Scope**: Wiki nodes for SCENIC+ pipeline implementation  
**Implementation plan**: `plans/scenicplus_implementation.md`

Files reviewed:
- New: `wiki/packages/pycisTopic.md`, `pycistarget.md`, `scenicplus.md`
- New: `wiki/stages/topic_modeling.md`, `wiki/methods/enhancer_grn.md`
- New: `wiki/tools/atac_topic_pycisTopic.md`, `multi_grn_pycistarget.md`, `multi_grn_peak_to_gene.md`, `multi_grn_scenicplus.md`, `multi_grn_scenicplus_aucell.md`, `rna_grn_pyscenic_aucell.md`
- Updated: `wiki/stages/grn_inference.md`, `wiki/methods/coexpression_grn.md`, `wiki/packages/pyscenic.md`, `wiki/resources/pyscenic_databases.md`

---

## Package files

### `wiki/packages/pycisTopic.md`

Correct: `create_cistopic_object` requires regions × cells (transposed from AnnData), `model.topic_region` is topic × peak (must transpose for `varm`), model selection warnings.

**[PKG-1] Missing: `n_topics` wrapping requirement**  
The plan explicitly flags that `run_cgs_models()` requires `n_topics: list[int]` and will fail or produce wrong results if passed a bare int. Not mentioned. Users will hit a confusing error if they pass a single int directly to the internal call.

**[PKG-2] Missing: temp file path guidance**  
The plan notes Gibbs sampling writes large temp files and recommends using `save_path` for per-model saving. Not documented — users running large datasets may fill `/tmp` unexpectedly.

---

### `wiki/packages/pycistarget.md`

Correct: wrapper import path from `scenicplus.wrappers`, PyRanges conversion requirement, annotation_version mismatch warning, menr dict structure.

No issues.

---

### `wiki/packages/scenicplus.md`

Correct: all key function → module mappings, dill serialization requirement, Ray parallelism note, AUCell called twice.

No issues.

---

## Stage files

### `wiki/stages/topic_modeling.md`

**[STAGE-1] Missing output key: `pycisTopic_model_path`**  
The Outputs section lists 4 keys. The plan specifies 5:
```
adata.uns["pycisTopic_model_path"]   # Path to pickled best LDA model
```
The tool wiki (`atac_topic_pycisTopic.md`) lists all 5 correctly. The stage wiki is inconsistent.

---

### `wiki/stages/grn_inference.md` (updated)

The `enhancer_grn` edge is correctly added.

**[STAGE-2] Body text doesn't reference SCENIC+**  
The prose says "For ATAC or multi-omic: pySCENIC with ATAC peaks as cis-regulatory evidence, or SnapATAC2's integrated motif–gene linking." SCENIC+ is the primary multi-omic GRN method added in this implementation and should be mentioned here alongside pySCENIC.

**[STAGE-3] Pre-existing error: pycisTopic listed under footprinting**  
The body text lists "pycisTopic, HINT-ATAC" under the "Footprinting" evidence source. pycisTopic performs LDA topic modeling, not TF footprinting. HINT-ATAC is footprinting. pycisTopic belongs under a separate entry (topic modeling / chromatin accessibility decomposition) or should be removed from that list. This predates this implementation but is surfaced by this review.

---

## Method files

### `wiki/methods/enhancer_grn.md`

Correct: three evidence layers, eGRN vs pySCENIC table, pseudoreplication warning, output DataFrame spec.

**[METHOD-1] Missing column: `importance_x_abs_rho`**  
The plan's eRegulon metadata DataFrame spec lists:
```
importance_x_rho      float
importance_x_abs_rho  float   ← missing from wiki
importance            float
rho                   float
```
The wiki omits `importance_x_abs_rho`. This column is produced by `format_egrns()` and is important for ranking eRegulons by absolute strength regardless of direction.

---

### `wiki/methods/coexpression_grn.md` (updated)

The `rna_grn_pyscenic_aucell` edge is correctly added.

No issues.

---

## Tool files

### `wiki/tools/atac_topic_pycisTopic.md`

Frontmatter correct. All 5 output keys documented. Model selection behavior, memory guard, and prerequisite chain all correct.

No issues.

---

### `wiki/tools/multi_grn_pycistarget.md`

**[TOOL-1] `annotation_version: v9` default inconsistent with recommended usage**  
The frontmatter default is `v9` (matching the plan's implementation default) but the documentation immediately warns that `v10nr_clust` should be used with the standard preset. Most users will use the standard preset and will need to override this. Consider whether the default should be `v10nr_clust` or whether the param description should be even more prominent. As-is, users who copy the frontmatter defaults will run with the wrong annotation_version.

**[TOOL-2] Missing params: `dem_max_bg_regions`, `dem_motif_hit_thr` descriptions**  
Both params appear in the plan's signature and in the frontmatter but are not described in the params list section. `dem_motif_hit_thr` in particular (default 3.0) affects DEM sensitivity.

---

### `wiki/tools/multi_grn_peak_to_gene.md`

**[TOOL-3] `chromsizes_path` not listed as a param**  
The plan specifies `chromsizes_path: str | Path | None = None` as an explicit offline fallback parameter. The wiki mentions "provide `chromsizes_path` pointing to a UCSC .chrom.sizes file" under the Gene annotation section but does not list it in the params description. Users won't know the parameter name.

**[TOOL-4] `n_cpu` not listed in params description**  
`n_cpu: 4` appears in the frontmatter but is missing from the params description section.

---

### `wiki/tools/multi_grn_scenicplus.md`

**[TOOL-5] `rho_dichotomize_*` booleans not documented**  
The plan specifies three booleans that individually control the activating/repressing split for each link type:
```python
rho_dichotomize_tf2g: bool = True
rho_dichotomize_r2g: bool = True
rho_dichotomize_eregulon: bool = True
```
None appear in the frontmatter params or the params description. Users who want to disable the direction split for a specific link type have no way to know these exist.

**[TOOL-6] `gsea_n_perm`, `quantiles`, `top_n_regionTogenes_per_gene` not described**  
All three are in the frontmatter params but absent from the params description section. `quantiles` and `top_n_regionTogenes_per_gene` are lists (non-scalar defaults) and need explanation — the plan describes their role in `build_grn()`.

**[TOOL-7] `"recompute"` sentinel not explained**  
Step 3 of the workflow says `coexpression_adj_path="recompute"` triggers internal recomputation using `calculate_TFs_to_genes_relationships()`. This sentinel value is not documented in the params section. Users reading only the params description will not know this string value triggers an alternate code path.

---

### `wiki/tools/multi_grn_scenicplus_aucell.md`

**[TOOL-8] `seed` param missing; `n_cpu` default differs from plan**  
The plan's frontmatter for this tool specifies:
```yaml
params:
  auc_threshold: 0.05
  seed: 42
  n_cpu: 4
```
The actual wiki has `n_cpu: 1` and no `seed`. AUCell uses random ranking for ties; `seed` is needed for reproducibility.

**[TOOL-9] `scplus_obj_key` and `eregulons_key` not documented**  
Both appear in the plan's tool signature but are not in the params description. Users can't change which uns keys the tool reads from.

---

### `wiki/tools/rna_grn_pyscenic_aucell.md`

Correct: AUCell algorithm description, obsm numpy array requirement, output keys, fallback to `scipy.stats.rankdata`.

No issues.

---

## Updated files

### `wiki/packages/pyscenic.md` (updated)

AUCell section correctly added. Three-stage description and output key (`X_pyscenic_auc`, `pyscenic_auc_tf_names`) correctly described.

**[PKG-3] Filename inconsistency with `pyscenic_databases.md`**  
`pyscenic.md` describes a database file as `hg38_500bp_up_100bp_down_full_tx_v10_clust.genes_vs_motifs.rankings.feather` (v10 naming). `pyscenic_databases.md` lists the `hg38_refseq_500bp` alias as `hg38__refseq-r80__500bp_up_and_100bp_down_tss.mc9nr.feather` (v9/mc9nr naming). These are different files from different database versions. The two nodes disagree on what "the standard database" is. This predates this implementation.

---

### `wiki/resources/pyscenic_databases.md` (updated)

SCENIC+ compatibility note added. `annotation_version` warning added.

**[RES-1] `annotation_version='v10nr_clust'` advice conflicts with listed files**  
This is the most critical finding. The note says:
> "set `annotation_version='v10nr_clust'` to match the database version"

But the database files listed in this same resource all use `mc9nr` naming (e.g. `hg38__refseq-r80__10kb_up_and_down_tss.mc9nr.feather`). These are v9-era files, not v10nr_clust. If a user has only the files listed in this resource, setting `annotation_version='v10nr_clust'` would make `run_pycistarget()` use the wrong annotation lookup — the exact silent failure the warning is trying to prevent.

The note should be:
> "The `annotation_version` must match your actual database files. If you are using the files listed in this resource (`mc9nr` filenames), use `annotation_version='v9'`. If you have downloaded `v10nr_clust` files separately, use `annotation_version='v10nr_clust'`."

This may also reveal that the resource needs to be updated to list v10nr_clust filenames if the system intends to use those files for SCENIC+.

---

## Summary Table

| ID | File | Severity | Description |
|----|------|----------|-------------|
| RES-1 | pyscenic_databases.md | **Critical** | `annotation_version='v10nr_clust'` advice conflicts with `mc9nr` files actually listed |
| PKG-3 | pyscenic.md | Medium | Database filename inconsistency with pyscenic_databases.md (v10 vs mc9nr) |
| TOOL-8 | multi_grn_scenicplus_aucell.md | Medium | `seed` param missing; `n_cpu` default changed from plan spec |
| TOOL-5 | multi_grn_scenicplus.md | Medium | `rho_dichotomize_*` booleans not documented |
| TOOL-7 | multi_grn_scenicplus.md | Medium | `"recompute"` sentinel not explained |
| METHOD-1 | enhancer_grn.md | Medium | `importance_x_abs_rho` column missing from eRegulon metadata spec |
| STAGE-1 | topic_modeling.md | Low | Missing `pycisTopic_model_path` output key |
| STAGE-2 | grn_inference.md | Low | Body text doesn't mention SCENIC+ despite edge being added |
| STAGE-3 | grn_inference.md | Low | Pre-existing: pycisTopic incorrectly listed under footprinting |
| TOOL-1 | multi_grn_pycistarget.md | Low | `annotation_version: v9` default misleading; most users need v10nr_clust |
| TOOL-2 | multi_grn_pycistarget.md | Low | `dem_max_bg_regions`, `dem_motif_hit_thr` not described |
| TOOL-3 | multi_grn_peak_to_gene.md | Low | `chromsizes_path` not listed as a param |
| TOOL-4 | multi_grn_peak_to_gene.md | Low | `n_cpu` missing from params description |
| TOOL-6 | multi_grn_scenicplus.md | Low | `gsea_n_perm`, `quantiles`, `top_n_regionTogenes_per_gene` not described |
| TOOL-9 | multi_grn_scenicplus_aucell.md | Low | `scplus_obj_key`, `eregulons_key` not documented |
| PKG-1 | pycisTopic.md | Low | `n_topics` must be list — wrapping requirement not mentioned |
| PKG-2 | pycisTopic.md | Low | Temp file path guidance absent |

### Priority fixes

1. **RES-1** — Fix annotation_version advice: clarify that mc9nr files → `annotation_version='v9'`, or update the resource to list v10nr_clust filenames if those are what the system actually uses.
2. **TOOL-8** — Add `seed: 42` to `multi_grn_scenicplus_aucell.md` frontmatter; restore `n_cpu: 4`.
3. **TOOL-5** — Document `rho_dichotomize_*` booleans in `multi_grn_scenicplus.md`.
4. **METHOD-1** — Add `importance_x_abs_rho` to `enhancer_grn.md` output spec.
5. **STAGE-1** — Add `pycisTopic_model_path` to `topic_modeling.md` outputs.

---

# SCENIC+ Backend Tools Code Review

**Reviewed**: 2026-05-14  
**Scope**: Backend tool implementations for the full SCENIC+ pipeline  
**Files reviewed**:
- `backend/tools/atac/topic/pycisTopic.py` (Tool 1)
- `backend/tools/multi/grn/pycistarget.py` (Tool 2)
- `backend/tools/multi/grn/peak_to_gene.py` (Tool 3)
- `backend/tools/multi/grn/scenicplus.py` (Tool 4)
- `backend/tools/multi/grn/scenicplus_aucell.py` (Tool 5)
- `backend/tools/rna/grn/pyscenic_aucell.py` (Tool 6)

**Reference**: `plans/scenicplus_implementation.md`

---

## Tool 1: `atac_topic_pycisTopic.py`

Correct: `n_topics` wrapping (`[n_topics] if isinstance(n_topics, int) else list(n_topics)`), memory guard (warn at 5e8, stop at 2e9), peak name assertion, `adata.X.T` transpose for CistopicObject, `run_cgs_models(save_path=...)`, multi-model raise behavior, `model.cell_topic` → `obsm["X_topic"]`, `model.topic_region.T` → `varm["topic_peak_weights"]`, CistopicObject pickle serialization, `n_top_peaks=500` topic region set construction.

**[T1-1] `pycisTopic_model_path` records an assumed path that may not match what `run_cgs_models()` actually writes**  
```python
model_path = output_dir / "topic_models" / f"model_{n_topics_list[0]}.pkl"
adata.uns["pycisTopic_model_path"] = str(model_path)
```
`run_cgs_models(save_path=models_save_path)` saves models with its own internal naming convention. The path `model_{n}.pkl` is assumed, not verified. If pycisTopic uses a different filename (e.g. `LDA_{n}_topics.pkl`), this pointer is wrong. The CistopicObject is still correctly saved — only the model path metadata is at risk.

---

## Tool 2: `multi_grn_pycistarget.py`

Correct: import from `scenicplus.wrappers.run_pycistarget`, `region_sets_key` validation, `output_dir` required guard, `_peaks_to_pyranges()` helper, `save_path` mapping, `path_to_motif_annotations` parameter name, menr.pkl load-back, TF-region summary DataFrame extraction.

**[T2-1] `menr.pkl` loaded with `dill` but may have been saved with `pickle`**  
`run_pycistarget()` internally saves `menr.pkl`. The implementation loads it with `dill.load()`. dill is backward-compatible with pickle, so this works if pycistarget uses pickle. If pycistarget uses dill internally (for complex CisTargetResult objects), `dill.load()` is exactly right. No bug — but if a future pycistarget version changes serialization, this silent dependency is worth monitoring.

---

## Tool 3: `multi_grn_peak_to_gene.py`

Correct: two-step workflow (search space → importance scoring), `correlation_scoring_method="SR"` explicit, importance/rho thresholds as post-hoc filters (not passed to SCENIC+ function), DataFrame conversion from AnnData before calling SCENIC+, `chromsizes_path` offline fallback, `n_obs < 200` warning.

**[T3-1] HIGH: `_fetch_gene_annotation()` ignores its `species` parameter — always fetches human**  
```python
def _fetch_gene_annotation(species: str, biomart_host: str | None):
    ...
    dataset_name = "hsapiens_gene_ensembl"  # hardcoded — species arg never used
    dataset = mart[dataset_name]
```
The function accepts `species` but the biomart dataset is hardcoded to `hsapiens_gene_ensembl`. Mouse or other organism data would silently use human TSS coordinates, producing systematically wrong search spaces and near-zero peak-gene links.

Fix: map `species` to the correct dataset name:
```python
_SPECIES_DATASET = {
    "homo_sapiens": "hsapiens_gene_ensembl",
    "mus_musculus": "mmusculus_gene_ensembl",
}
dataset_name = _SPECIES_DATASET.get(species, "hsapiens_gene_ensembl")
```

**[T3-2] HIGH: `_fetch_chromsizes_biomart()` hardcodes human chromosome sizes**  
```python
dataset = mart["hsapiens_gene_ensembl"]  # always human; no species parameter
```
`run()` and `_run_peak_to_gene()` have no `species` parameter — there is no path to pass the correct organism for automatic biomart fetches. Mouse users who don't pre-supply `gene_annotation` and `chromsizes` objects will get human coordinates without any warning.

Fix: add a `species: str = "homo_sapiens"` parameter to `run()` and thread it through to both biomart fetch helpers.

**[T3-3] Concurrent runs collide on `/tmp/r2g_tmp`**  
```python
r2g_tmp = (output_dir / "r2g_tmp") if output_dir else Path("/tmp/r2g_tmp")
```
When `output_dir=None`, all concurrent pipeline runs write to the same `/tmp/r2g_tmp`. Minor on single-machine pipelines; real collision risk in multi-process DAGs.

---

## Tool 4: `multi_grn_scenicplus.py`

The module docstring explicitly flags that this implementation uses a **newer `build_grn()` API** that differs from the plan specification. The plan describes `build_grn(scplus_obj, adj_key=..., cistromes_key=..., ...)` (SCENICPLUS-object-based); the implementation uses `build_grn(tf_to_gene, region_to_gene, cistromes, is_extended, ...)` (DataFrame-based). This discrepancy is documented and intentional. All findings below are evaluated against the newer API as implemented.

Correct: artifact path resolution from `adata.uns`, file-existence assertions, RNA AnnData loading, CistopicObject pickle load, menr dill load, `create_SCENICPLUS_object(multi_ome_mode=True)`, TF2G adj loaded into `scplus_obj.uns["TF2G_adj"]` via `load_TF2G_adj_from_file`, r2g stored as `scplus_obj.uns["region_to_gene"]`, `build_grn()` called twice (direct + extended cistromes), eRegulons stored on `scplus_obj.uns["eRegulons"]` before `format_egrns`, dill serialization of scplus_obj.

**[T4-1] `merge_cistromes(scplus_obj)` not called — plan-required step replaced by manual extraction**  
The plan requires `merge_cistromes(scplus_obj)` before `build_grn()` to convert menr into cistromes stored on scplus_obj:
```python
# Plan Step 2 (not present in implementation):
from scenicplus.cistromes import merge_cistromes
merge_cistromes(scplus_obj)
```
The implementation substitutes this with `_extract_cistromes_from_menr()`, which manually builds cistrome AnnData objects and passes them directly to `build_grn(cistromes=...)`. This approach is consistent with the newer DataFrame-based `build_grn()` API, but depends on the cistromes AnnData format being what `build_grn()` expects. If the newer API uses a different structure (e.g., a dict or a list), this will fail silently by producing no eRegulons.

**[T4-2] MEDIUM: `_extract_cistromes_from_menr()` fallback path relies on undocumented pycistarget attributes**  
The primary path (`result.cistromes`) is standard. The fallback path via `pycistarget.utils.get_TF_list`, `get_motifs_per_TF`, and `result.motif_hits` are not confirmed public pycistarget API:
```python
from pycistarget.utils import get_TF_list, get_motifs_per_TF
...
if hasattr(result, "motif_hits"):
    for motif in motifs:
        if motif in result.motif_hits:
            regions.update(result.motif_hits[motif])
```
If neither `result.cistromes` nor `result.motif_hits` exists on the actual pycistarget result objects, `_extract_cistromes_from_menr()` will log warnings per-topic and return empty cistromes, causing `build_grn()` to produce no eRegulons with no clear error.

**[T4-3] MEDIUM: `build_grn()` API version mismatch is undocumented at runtime**  
If the installed SCENIC+ version still uses the plan's scplus_obj-based API, the call:
```python
build_grn(
    cistromes=direct_cistromes,
    is_extended=False,
    tf_to_gene=tf2g_df,
    ...
)
```
will raise a `TypeError: unexpected keyword argument` with no clear indication of the API version mismatch. The module docstring documents the discrepancy, but there is no runtime version check. Recommend pinning `scenic-plus` in `requirements.txt` to the version whose API matches.

**[T4-4] MEDIUM: `gsea_n_perm` may not be a valid parameter for the newer `build_grn()` API**  
`gsea_n_perm=gsea_n_perm` is included in `build_grn_kwargs`. The plan describes this parameter for the old API. If the newer API does not accept it, both `build_grn()` calls will raise `TypeError`. This should be verified against the installed SCENIC+ version.

**[T4-5] `_score_aucell()` called with hardcoded `auc_threshold=0.05` and `n_cpu=1`**  
```python
if run_aucell and len(eregulon_df) > 0:
    _score_aucell(adata, rna_adata, eregulon_df, auc_threshold=0.05, n_cpu=1)
```
The `run()` function has `n_cpu: int = 4` as a parameter, but it is not threaded into the internal AUCell call. For large datasets, single-threaded AUCell is significantly slower. The `auc_threshold` is also not exposed — users cannot tune it except by running `multi_grn_scenicplus_aucell` separately.

Fix:
```python
_score_aucell(adata, rna_adata, eregulon_df, auc_threshold=0.05, n_cpu=n_cpu)
```
And optionally add `auc_threshold: float = 0.05` to `run()`'s signature.

**[T4-6] RNA-based AUC stored on ATAC `adata.obsm` with no barcode alignment check**  
```python
adata.obsm["X_scenicplus_rna_auc"] = rna_auc_df.values
```
`rna_auc_df` has rows indexed by `rna_adata.obs_names`; `adata` is the ATAC object. In correctly constructed multi-ome data these are the same barcodes, but if they differ, `obsm` assignment will either fail with a shape error or silently store misaligned data.

Fix: add `assert list(rna_adata.obs_names) == list(adata.obs_names)` (or a set-intersection check) before storing.

---

## Tool 5: `multi_grn_scenicplus_aucell.py`

The module docstring explicitly documents the newer API: `score_eRegulons(eRegulons, gex_mtx, acc_mtx, ...)` returning a dict of DataFrames, with no separate `make_rankings()` step. This is consistent with Tool 4's internal `_score_aucell()`.

Correct: eRegulons DataFrame → gex_df/acc_df conversion, `score_eRegulons()` call, `.values` extraction before `obsm` assignment, `celltype_key` guard, eRegulon count/TF/region/target tallying.

**[T5-1] `rna_adata` is a positional parameter — inconsistent with other tools**  
```python
def run(
    adata,
    rna_adata=None,        # positional with default
    *,
    rna_h5ad_path: ...,    # keyword-only starts here
    ...
)
```
All other tools in this codebase use `def run(adata, *, ...)` where everything after `adata` is keyword-only. Having `rna_adata` as a positional parameter means callers can pass it without the keyword, which is inconsistent and can cause confusing errors (e.g., `run(adata, "path/to/rna.h5ad")` would assign the path string to `rna_adata`, not `rna_h5ad_path`).

Fix: move `rna_adata` after `*`:
```python
def run(adata, *, rna_adata=None, rna_h5ad_path=None, ...):
```

**[T5-2] HIGH: `_compute_rss()` produces one score per cell type, not per (regulon, cell type)**  
```python
for ct in unique_types:
    mask = cell_type_labels == ct
    ct_auc = auc_df[mask].mean(axis=0).values + 1e-10   # mean AUC across cells of this type
    bg_auc = auc_df[~mask].mean(axis=0).values + 1e-10   # mean AUC across all other cells
    p = ct_auc / ct_auc.sum()   # treat mean AUC profile as a distribution
    q = bg_auc / bg_auc.sum()
    js = 0.5 * (kl_div(p, m).sum() + kl_div(q, m).sum())
    rss_records[ct] = 1 - js   # scalar per cell type
```
The result is a `(n_cell_types × 1)` DataFrame with one RSS scalar per cell type. Standard SCENIC+ RSS is a `(n_cell_types × n_regulons)` matrix where each entry quantifies how specific that regulon is for that cell type. The current implementation collapses all regulons into one JSD score, making it impossible to identify which regulons are cell-type-specific.

Fix: compute RSS per regulon:
```python
rss_matrix = {}
for ct in unique_types:
    mask = cell_type_labels == ct
    ct_auc = auc_df[mask].mean(axis=0) + 1e-10   # Series, length = n_regulons
    bg_auc = auc_df[~mask].mean(axis=0) + 1e-10
    # Normalize each regulon independently as a 2-point distribution
    p = ct_auc / (ct_auc + bg_auc)
    q = 1.0 - p
    rss_matrix[ct] = (p * np.log2(p / 0.5) + q * np.log2(q / 0.5)).values  # Jensen-Shannon
pd.DataFrame(rss_matrix, index=auc_df.columns).T  # (n_cell_types × n_regulons)
```

---

## Tool 6: `rna_grn_pyscenic_aucell.py`

Correct: `pyscenic.aucell` try-import with manual fallback, `create_rankings(expr_df, seed=seed)`, `frozenset` targets, `.values` before `obsm`, sparse X handling, CSV output when `output_dir` set.

**[T6-1] `_aucell_manual()` uses a simplified hit-fraction formula, not the real AUC**  
```python
hits = np.sum(sorted_ranks <= n_top)
return float(hits) / len(ranks)
```
The correct AUC integrates the area under the recall curve (cumulative fraction of target genes recovered as the rank threshold increases, divided by `n_top`). The implementation counts hits in the top `n_top` positions and divides by the number of target genes. This produces values in a different range and with different sensitivity. Scores from the fallback and from `pyscenic.aucell` are not comparable.

**[T6-2] `max_auc` is a dead variable in `_auc_from_ranks()`**  
```python
max_auc = float(n_top) * len(ranks)   # computed but never used
if max_auc == 0:
    return 0.0
```
`max_auc` is computed, used in the zero-guard, but never used as a denominator. The guard `if max_auc == 0` would never be true in practice (both `n_top` and `len(ranks)` are positive integers). Remove the variable or use it correctly in the normalization.

---

## Summary Table

| ID | Tool | File | Severity | Description |
|----|------|------|----------|-------------|
| T3-1 | peak_to_gene | `peak_to_gene.py` | **High** | `_fetch_gene_annotation()` ignores species — always fetches human TSS |
| T3-2 | peak_to_gene | `peak_to_gene.py` | **High** | `_fetch_chromsizes_biomart()` hardcodes human; no species param in `run()` |
| T5-2 | scenicplus_aucell | `scenicplus_aucell.py` | **High** | `_compute_rss()` returns 1 scalar per cell type, not (n_cell_types × n_regulons) matrix |
| T4-2 | scenicplus | `scenicplus.py` | Medium | Fallback cistrome extraction uses unconfirmed pycistarget private attributes |
| T4-3 | scenicplus | `scenicplus.py` | Medium | `build_grn()` API version mismatch causes opaque TypeError with no version hint |
| T4-4 | scenicplus | `scenicplus.py` | Medium | `gsea_n_perm` may not be valid for newer `build_grn()` API |
| T4-5 | scenicplus | `scenicplus.py` | Medium | `_score_aucell()` called with hardcoded `n_cpu=1`; `n_cpu` from caller not threaded through |
| T4-6 | scenicplus | `scenicplus.py` | Medium | RNA AUC stored on ATAC adata with no barcode alignment assertion |
| T6-1 | pyscenic_aucell | `pyscenic_aucell.py` | Medium | Manual AUC fallback uses hit fraction, not area under recall curve — not comparable to `pyscenic.aucell` |
| T1-1 | pycisTopic | `pycisTopic.py` | Low | `pycisTopic_model_path` assumes pycisTopic file naming convention |
| T3-3 | peak_to_gene | `peak_to_gene.py` | Low | `/tmp/r2g_tmp` collision when `output_dir=None` |
| T4-1 | scenicplus | `scenicplus.py` | Low | `merge_cistromes()` replaced by `_extract_cistromes_from_menr()` — compatibility with `build_grn()` format unverified |
| T5-1 | scenicplus_aucell | `scenicplus_aucell.py` | Low | `rna_adata` is positional, not keyword-only; inconsistent with other tools |
| T6-2 | pyscenic_aucell | `pyscenic_aucell.py` | Low | `max_auc` dead variable in `_auc_from_ranks()` |
| T2-1 | pycistarget | `pycistarget.py` | Low | `dill.load()` for menr.pkl saved by pycistarget — silent dependency on serialization format |

### Priority fixes before integration testing

1. **T3-1 / T3-2** — Add `species: str = "homo_sapiens"` to `peak_to_gene.run()` and thread it into `_fetch_gene_annotation()` and `_fetch_chromsizes_biomart()` with a `_SPECIES_DATASET` mapping. Without this, all non-human runs silently use wrong coordinates.
2. **T5-2** — Rewrite `_compute_rss()` to return a `(n_cell_types × n_regulons)` DataFrame, computing per-regulon specificity rather than a collapsed scalar.
3. **T4-5** — Thread `n_cpu` from `run()` into `_score_aucell()`. Optionally expose `auc_threshold` in `run()`.
4. **T4-4** — Verify whether `gsea_n_perm` is accepted by the installed `build_grn()` API; remove from `build_grn_kwargs` if not.
5. **T4-6** — Add barcode alignment assertion before storing RNA AUC on ATAC adata.

---

# SCENIC+ Backend Tools Re-Review (Post-Correction)

**Reviewed**: 2026-05-14 (second pass)
**Scope**: Re-review of all 6 backend tool implementations after user corrections
**Files reviewed**:
- `backend/tools/atac/topic/pycisTopic.py` (Tool 1) — unchanged
- `backend/tools/multi/grn/pycistarget.py` (Tool 2) — unchanged
- `backend/tools/multi/grn/peak_to_gene.py` (Tool 3) — updated
- `backend/tools/multi/grn/scenicplus.py` (Tool 4) — updated
- `backend/tools/multi/grn/scenicplus_aucell.py` (Tool 5) — updated
- `backend/tools/rna/grn/pyscenic_aucell.py` (Tool 6) — updated

---

## Fixes Confirmed

The following issues from the first review were correctly resolved:

| ID | File | Fix applied |
|----|------|-------------|
| T3-1 | `peak_to_gene.py` | `_fetch_gene_annotation()` now accepts `species` and uses `_SPECIES_DATASET.get(species, ...)` |
| T3-2 | `peak_to_gene.py` | `_fetch_chromsizes_biomart()` likewise uses `_SPECIES_DATASET`; `species` threaded through `run()` |
| T3-3 | `peak_to_gene.py` | `tempfile.mkdtemp(prefix="r2g_tmp_")` used when `output_dir=None`; collision eliminated |
| T4-5 | `scenicplus.py` | `_score_aucell()` now called with `n_cpu=n_cpu` (no longer hardcoded `n_cpu=1`) |
| T4-6 | `scenicplus.py` | Barcode alignment check added at start of `_score_aucell()`; raises `ValueError` on mismatch |
| T5-1 | `scenicplus_aucell.py` | `rna_adata` moved after `*` — now keyword-only, consistent with other tools |
| T5-2 | `scenicplus_aucell.py` | `_compute_rss()` rewritten to produce `(n_cell_types × n_regulons)` DataFrame using per-regulon 2-point JSD |
| T6-1 | `pyscenic_aucell.py` | `_auc_from_ranks()` now computes correct trapezoidal AUC: `(n_top - in_top + 1).sum() / (n_top * n_targets)` |
| T6-2 | `pyscenic_aucell.py` | Dead `max_auc` variable eliminated; function fully rewritten |

---

## Still Open from First Review

The following first-review findings remain unaddressed:

**[T1-1] LOW — `pycisTopic_model_path` records an assumed filename** (`pycisTopic.py`)
`run_cgs_models(save_path=...)` saves models with its own internal naming convention. The pointer `model_{n_topics_list[0]}.pkl` is assumed, not verified. No change made.

**[T2-1] LOW — `dill.load()` for `menr.pkl`** (`pycistarget.py`)
pycistarget's serialization format is not pinned. No change made. Still a monitoring concern.

**[T4-1] LOW — `merge_cistromes()` not called; manual `_extract_cistromes_from_menr()` substituted** (`scenicplus.py`)
Compatibility with the `build_grn(cistromes=...)` format is unverified. No change made.

**[T4-2] MEDIUM — `_extract_cistromes_from_menr()` uses unconfirmed pycistarget attributes** (`scenicplus.py`)
`result.cistromes`, `result.motif_hits`, `pycistarget.utils.get_TF_list/get_motifs_per_TF` are not confirmed public API. No change made.

**[T4-3] MEDIUM — `build_grn()` API version mismatch causes opaque `TypeError`** (`scenicplus.py`)
No runtime version check or pinned requirement added. No change made.

**[T4-4] MEDIUM — `gsea_n_perm` may not be valid for newer `build_grn()` API** (`scenicplus.py`)
Not verified against installed SCENIC+ version. No change made.

---

## New Findings (Post-Correction)

### Tool 3: `peak_to_gene.py`

**[NEW-4] LOW — Chromosome filter regex drops Drosophila arm chromosomes**
Both biomart helpers apply this filter:
```python
result = result[result["Chromosome"].str.match(r"^chr\d+$|^chrX$|^chrY$")]
```
This pattern requires `chr` followed by purely numeric digits, `X`, or `Y`. Drosophila chromosomes (chr2L, chr2R, chr3L, chr3R, chr4, chrX) include letter suffixes — only `chrX` and `chr4` pass. The major arms (chr2L, chr2R, chr3L, chr3R) are silently dropped, leaving near-zero search space for Drosophila users. The `_SPECIES_DATASET` dict already supports `drosophila_melanogaster`, but the filter undermines it.

Fix: use a broader fallback that still excludes random/patch sequences:
```python
result = result[result["Chromosome"].str.match(r"^chr[\w]+$")]
# Or more conservatively, allow common arm suffixes:
result = result[result["Chromosome"].str.match(r"^chr(\d+|X|Y|[2-4][LR]?)$")]
```

**[NEW-5] LOW — Biomart returns strand as integers; `get_search_space()` may expect `"+"`/`"-"`**
Ensembl biomart encodes strand as `1` (forward) and `-1` (reverse) in numeric columns. The implementation stores this as-is in the `Strand` column. `scenicplus.data_wrangling.gene_search_space.get_search_space()` may expect `"+"` and `"-"` string encoding for strand-aware TSS offset calculation. If it does, forward-strand TSS positions will be used for all genes regardless of strand, causing upstream/downstream windows to be computed in the wrong direction.

Verification needed: check `get_search_space()` source for strand encoding requirement. Fix if needed:
```python
result["Strand"] = result["Strand"].map({1: "+", -1: "-"})
```

---

### Tool 4: `scenicplus.py`

**[NEW-2] LOW — `/tmp/scenicplus_tmp` hardcoded when `output_dir=None`**
The temp directory for the SCENIC+ build step is hardcoded:
```python
tmp_dir = output_dir / "scenicplus_tmp" if output_dir else Path("/tmp/scenicplus_tmp")
```
The same fix applied to `peak_to_gene.py` (use `tempfile.mkdtemp()`) was not applied here. Concurrent runs on the same machine will share the same temp path and can corrupt each other's intermediate files.

Fix:
```python
import tempfile
tmp_dir = output_dir / "scenicplus_tmp" if output_dir else Path(tempfile.mkdtemp(prefix="scenicplus_tmp_"))
```

**[NEW-3] LOW — `auc_threshold` hardcoded in internal AUCell call**
After T4-5 was fixed (`n_cpu` is now threaded through), `auc_threshold` remains hardcoded:
```python
_score_aucell(adata, rna_adata, eregulon_df, auc_threshold=0.05, n_cpu=n_cpu)
```
Users cannot tune AUCell stringency from the `multi_grn_scenicplus` tool without running `multi_grn_scenicplus_aucell` separately. Minor usability issue since the standalone tool exists, but inconsistent with `n_cpu` being configurable.

Fix: add `auc_threshold: float = 0.05` to `run()` and thread through.

---

### Tool 5: `scenicplus_aucell.py`

**[NEW-1] LOW — `_compute_rss()` produces NaN for all cell types when only one cell type is present**
The T5-2 fix computes background AUC using `auc_df[~mask]`. When there is only one cell type, `~mask` is entirely `False` and `auc_df[~mask]` is an empty DataFrame. `.mean(axis=0)` on an empty DataFrame returns `NaN` for all columns. The subsequent arithmetic (`NaN + 1e-10 = NaN`) propagates through the JSD calculation, producing a row of NaN for that cell type.

This edge case arises in unit tests, highly purified cell populations, or early-stage analysis with a single annotated cluster.

Fix: guard against empty background:
```python
if mask.all():
    # Only one cell type — RSS is undefined; fill with 0 (no specificity meaningful to compute)
    rss_records[ct] = np.zeros(len(auc_df.columns), dtype=np.float32)
    continue
bg_auc = auc_df[~mask].mean(axis=0).values + 1e-10
```

---

## Updated Summary Table (All Outstanding Issues)

| ID | Tool | File | Severity | Status | Description |
|----|------|------|----------|--------|-------------|
| T4-2 | scenicplus | `scenicplus.py` | **Medium** | Open | Fallback cistrome extraction uses unconfirmed private pycistarget attributes |
| T4-3 | scenicplus | `scenicplus.py` | **Medium** | Open | `build_grn()` API mismatch raises opaque `TypeError` with no version hint |
| T4-4 | scenicplus | `scenicplus.py` | **Medium** | Open | `gsea_n_perm` may not be valid for newer `build_grn()` API |
| NEW-4 | peak_to_gene | `peak_to_gene.py` | Low | **New** | Chromosome filter regex drops Drosophila arm chromosomes (chr2L/2R/3L/3R) |
| NEW-5 | peak_to_gene | `peak_to_gene.py` | Low | **New** | Biomart strand integers (1/-1) may not match `get_search_space()` string expectation |
| NEW-2 | scenicplus | `scenicplus.py` | Low | **New** | `/tmp/scenicplus_tmp` hardcoded; concurrent-run collision (same fix as T3-3 not applied) |
| NEW-3 | scenicplus | `scenicplus.py` | Low | **New** | `auc_threshold=0.05` hardcoded in internal AUCell call; not user-configurable |
| NEW-1 | scenicplus_aucell | `scenicplus_aucell.py` | Low | **New** | `_compute_rss()` produces all-NaN row when only one cell type exists |
| T1-1 | pycisTopic | `pycisTopic.py` | Low | Open | `pycisTopic_model_path` assumes pycisTopic's internal file naming |
| T2-1 | pycistarget | `pycistarget.py` | Low | Open | `dill.load()` for menr.pkl — silent dependency on pycistarget serialization format |
| T4-1 | scenicplus | `scenicplus.py` | Low | Open | `merge_cistromes()` replaced by manual extraction; `build_grn()` format unverified |

### Priority fixes for next round

1. **T4-2 / T4-3 / T4-4** — These three together represent the core `build_grn()` integration risk. Pin `scenic-plus` to the specific version whose DataFrame-based API is implemented; add a `__version__` check at import time; verify `gsea_n_perm` is accepted.
2. **NEW-4** — Fix the chromosome regex to include arm-suffixed chromosomes; Drosophila support is otherwise dead on arrival.
3. **NEW-5** — Verify `get_search_space()` strand encoding requirement; add `.map({1: "+", -1: "-"})` if needed.
4. **NEW-2** — Apply `tempfile.mkdtemp(prefix="scenicplus_tmp_")` for consistency with the T3-3 fix.
5. **NEW-1** — Add single-cell-type guard in `_compute_rss()`.
6. **NEW-3** — Expose `auc_threshold` in `multi_grn_scenicplus.run()` and thread through to `_score_aucell()`.

---

# SCENIC+ Backend Tools Re-Review (Third Pass)

**Reviewed**: 2026-05-14 (third pass)
**Scope**: Re-review of all 6 backend tool implementations after second round of user corrections
**Files reviewed**:
- `backend/tools/atac/topic/pycisTopic.py` (Tool 1) — unchanged
- `backend/tools/multi/grn/pycistarget.py` (Tool 2) — unchanged
- `backend/tools/multi/grn/peak_to_gene.py` (Tool 3) — unchanged
- `backend/tools/multi/grn/scenicplus.py` (Tool 4) — updated
- `backend/tools/multi/grn/scenicplus_aucell.py` (Tool 5) — unchanged
- `backend/tools/rna/grn/pyscenic_aucell.py` (Tool 6) — unchanged

---

## Fixes Confirmed

No previously-open issues were resolved in this round. All 11 items from the second re-review remain open (see "Still Open" below).

---

## Partial Improvements (Not Full Fixes)

Two code-quality improvements were made to `scenicplus.py` that don't close any open issue but improve failure visibility:

**`_extract_cistromes_from_menr()` now raises `RuntimeError` on total failure** (lines 216–222)
```python
if not all_direct and not all_extended:
    raise RuntimeError(
        "No cistromes could be extracted from the menr dict. ..."
    )
```
Previously, a complete extraction failure returned empty AnnData objects silently, which would cause `build_grn()` to produce no eRegulons with no clear error. The RuntimeError converts this into an explicit failure at the right point. T4-2 (private attribute fallback) remains open — the exception applies only to the case where both paths fail for all topics.

**`_cistromes_dict_to_adata()` helper added** (lines 230–252)
A dedicated helper converts `{TF: set_of_regions}` to a boolean sparse AnnData (regions × TFs). This is a clean refactor of the cistrome formatting. T4-1 remains open — the fundamental question of whether `build_grn(cistromes=<this AnnData>)` expects this exact format is still unverified.

---

## Still Open from Second Review

All 11 items remain unresolved:

| ID | File | Severity | Description |
|----|------|----------|-------------|
| T4-2 | `scenicplus.py` | **Medium** | Fallback cistrome path uses unconfirmed pycistarget private attributes |
| T4-3 | `scenicplus.py` | **Medium** | `build_grn()` DataFrame-based API mismatch; no version check or pinned requirement |
| T4-4 | `scenicplus.py` | **Medium** | `gsea_n_perm` unverified for newer `build_grn()` API |
| NEW-4 | `peak_to_gene.py` | Low | Chromosome regex `^chr\d+$\|^chrX$\|^chrY$` drops Drosophila arm chromosomes |
| NEW-5 | `peak_to_gene.py` | Low | Biomart returns strand as int (1/-1); `get_search_space()` may expect `"+"`/`"-"` |
| NEW-2 | `scenicplus.py` | Low | `/tmp/scenicplus_tmp` hardcoded when `output_dir=None` |
| NEW-3 | `scenicplus.py` | Low | `auc_threshold=0.05` hardcoded in `_score_aucell()` call; not user-configurable |
| NEW-1 | `scenicplus_aucell.py` | Low | `_compute_rss()` produces all-NaN row when only one cell type present |
| T1-1 | `pycisTopic.py` | Low | `pycisTopic_model_path` assumes pycisTopic's internal file naming convention |
| T2-1 | `pycistarget.py` | Low | `dill.load()` for menr.pkl depends on pycistarget serialization format |
| T4-1 | `scenicplus.py` | Low | `merge_cistromes()` replaced by manual extraction; `build_grn()` AnnData format unverified |

---

## New Finding (Third Pass)

### Tool 4: `scenicplus.py`

**[NEW-6] LOW — `/tmp/grnboost2_adj.tsv` hardcoded when `output_dir=None`** (line 358–361)

```python
adj_file = (
    Path(output_dir) / "grnboost2_adj.tsv"
    if output_dir else Path("/tmp/grnboost2_adj.tsv")
)
```

When `output_dir` is not set and GRNBoost2 adjacencies are being written from `adata.uns["grnboost2_adjacencies"]`, the TSV is written to the same fixed path `/tmp/grnboost2_adj.tsv` for every run. Concurrent pipeline executions will silently overwrite each other's adjacency file, causing one run to load another run's TF-gene relationships. This is the same class of bug as NEW-2 (`/tmp/scenicplus_tmp`).

Fix: use `tempfile.NamedTemporaryFile` or write alongside the existing `r2g_tmp` tempdir:
```python
import tempfile
adj_file = (
    Path(output_dir) / "grnboost2_adj.tsv"
    if output_dir
    else Path(tempfile.mkstemp(suffix="_grnboost2_adj.tsv")[1])
)
```

---

## Updated Summary Table (All Outstanding Issues)

| ID | Tool | File | Severity | Status | Description |
|----|------|------|----------|--------|-------------|
| T4-2 | scenicplus | `scenicplus.py` | **Medium** | Open | Fallback cistrome extraction uses unconfirmed private pycistarget attributes |
| T4-3 | scenicplus | `scenicplus.py` | **Medium** | Open | `build_grn()` API mismatch; no version check or pinned requirement |
| T4-4 | scenicplus | `scenicplus.py` | **Medium** | Open | `gsea_n_perm` unverified for newer `build_grn()` API |
| NEW-4 | peak_to_gene | `peak_to_gene.py` | Low | Open | Chromosome regex drops Drosophila arm chromosomes (chr2L/2R/3L/3R) |
| NEW-5 | peak_to_gene | `peak_to_gene.py` | Low | Open | Biomart strand ints (1/-1) may not match `get_search_space()` string expectation |
| NEW-2 | scenicplus | `scenicplus.py` | Low | Open | `/tmp/scenicplus_tmp` hardcoded; concurrent-run collision |
| NEW-6 | scenicplus | `scenicplus.py` | Low | **New** | `/tmp/grnboost2_adj.tsv` hardcoded; concurrent-run collision |
| NEW-3 | scenicplus | `scenicplus.py` | Low | Open | `auc_threshold=0.05` hardcoded in internal AUCell call |
| NEW-1 | scenicplus_aucell | `scenicplus_aucell.py` | Low | Open | `_compute_rss()` all-NaN when only one cell type present |
| T1-1 | pycisTopic | `pycisTopic.py` | Low | Open | `pycisTopic_model_path` assumes pycisTopic's internal file naming |
| T2-1 | pycistarget | `pycistarget.py` | Low | Open | `dill.load()` for menr.pkl — silent dependency on serialization format |
| T4-1 | scenicplus | `scenicplus.py` | Low | Open | `merge_cistromes()` replaced by manual extraction; `build_grn()` AnnData format unverified |

### Priority fixes for next round

1. **T4-2 / T4-3 / T4-4** — Core `build_grn()` integration risk. Pin `scenic-plus` version; verify `gsea_n_perm`, `merge_eRegulons`, `NES_thr`, `adj_pval_thr` are all accepted by the installed version's API.
2. **NEW-4** — Fix chromosome regex to pass Drosophila arm chromosomes; Drosophila `_SPECIES_DATASET` entry is otherwise non-functional.
3. **NEW-5** — Add `.map({1: "+", -1: "-"})` after the biomart Strand column assignment in `_fetch_gene_annotation()`; verify `get_search_space()` strand encoding requirement.
4. **NEW-2 / NEW-6** — Apply `tempfile.mkdtemp()` / `tempfile.mkstemp()` to both hardcoded `/tmp` paths in `scenicplus.py`.
5. **NEW-1** — Add empty-background guard in `_compute_rss()` before calling `.mean()` on `auc_df[~mask]`.
6. **NEW-3** — Add `auc_threshold: float = 0.05` to `run()` in `scenicplus.py` and thread through to `_score_aucell()`.
