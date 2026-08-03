# SCENIC+ Implementation Plan

## Overview

SCENIC+ (Bravo González-Blas et al. 2023, *Nature Methods*) infers enhancer-driven gene
regulatory networks (eGRNs) from paired scRNA + scATAC data. It produces eRegulons: triplets
of `(TF, regulatory_regions, target_genes)` with directionality and multi-modal activity scores.

This plan covers all five components, their tool IDs, prerequisite chains, file artifacts,
implementation notes, and implementation order.

---

## Component → Tool Mapping

| Component | Package | Tool ID | Modality | Stage |
|---|---|---|---|---|
| LDA topic model on peaks | pycisTopic | `atac_topic_pycisTopic` | atac | `topic_modeling` |
| cisTarget motif enrichment on regions | pycistarget | `multi_grn_pycistarget` | multi | `grn_inference` |
| Peak-to-gene correlation (SCENIC+ style) | scenicplus | `multi_grn_peak_to_gene` | multi | `grn_inference` |
| eRegulon inference | scenicplus | `multi_grn_scenicplus` | multi | `grn_inference` |
| eRegulon AUCell scoring | scenicplus | `multi_grn_scenicplus_aucell` | multi | `grn_inference` |
| AUCell scoring for pySCENIC regulons | pyscenic | `rna_grn_pyscenic_aucell` | rna | `grn_inference` |

The last tool (`rna_grn_pyscenic_aucell`) was identified as missing from the existing pySCENIC
implementation and is included here since it uses the same AUCell machinery.

---

## Prerequisite Dependency Graph

```
atac_peak_calling_macs2 or atac_peak_calling_macs3
    → atac_topic_pycisTopic          (peak × cell count matrix → topics)
        serializes to disk:           cistopic_object.pkl  (full CistopicObject)
                                      topic_models/*.pkl   (LDA models)
        → multi_grn_pycistarget      (topic region sets → TF-region motif enrichment)
            serializes to disk:       menr.pkl             (run_pycistarget() menr dict)

rna_grn_grnboost2                    (RNA → TF → gene co-expression)

multi_grn_peak_to_gene               (paired RNA+ATAC → region → gene links)
    requires: atac_peak_calling + RNA h5ad

multi_grn_scenicplus                 (constructs SCENICPLUS object + infers eRegulons)
    requires: cistopic_object.pkl        (from atac_topic_pycisTopic)
              menr.pkl                   (from multi_grn_pycistarget)
              grnboost2_adjacencies      (from rna_grn_grnboost2 — in adata.uns, or adj .tsv path)
              scenicplus_peak_gene_links (from multi_grn_peak_to_gene — in adata.uns)
    internal steps:
              create_SCENICPLUS_object() → merge_cistromes()
              → load_TF2G_adj_from_file() or calculate_TFs_to_genes_relationships()
              → build_grn()  [standalone function from scenicplus.grn_builder.gsea_approach]

multi_grn_scenicplus_aucell          (eRegulons → per-cell AUC scores, re-scoring)
    requires: multi_grn_scenicplus
```

GRNBoost2 (`rna_grn_grnboost2`) is already implemented. Peak calling tools are already
implemented. The dependency chain above is additive on existing tools.

---

## Reuse Assessment: Existing Tools

### `atac_peak_to_gene_correlation` — NOT reusable for SCENIC+

Differences that block reuse:

| Aspect | Existing tool | SCENIC+ requirement |
|---|---|---|
| Window | 500kb (configurable) | ±150kb from TSS (separate upstream/downstream) |
| Correlation | Pearson, no FDR | Spearman + permutation-based background |
| TSS annotation | GTF file (manual) | Biomart or prebuilt annotation |
| Output key | `adata.uns["peak_gene_links"]` as list of dicts | DataFrame with `importance`, `correlation`, `p-value` columns |
| Integration | Standalone | Must feed directly into SCENIC+ eRegulon inference |

A new `multi_grn_peak_to_gene` tool is required. The existing tool remains valid for
standalone non-SCENIC+ workflows.

### `atac_motif_enrichment` — NOT reusable for SCENIC+

Differences:

| Aspect | Existing tool | SCENIC+ requirement |
|---|---|---|
| Database | JASPAR2024 via snapatac2 | cisTarget feather ranking databases |
| Input | DA peaks (group-level) | pycisTopic topic region sets as `pr.PyRanges` |
| Method | Hypergeometric enrichment | cisTarget ranking-based (DEM) |
| Output | Per-group enrichment table | Full pycistarget result object (not just a DataFrame) |

A new `multi_grn_pycistarget` tool is required.

### `resources/pyscenic_databases` — REUSABLE

pycistarget uses the same cisTarget feather databases and motif annotation files as
pySCENIC. Existing presets (`human`, `mouse`, `human_with_screen`) apply unchanged.
No new resource node required.

---

## New Type: `eGRN`

Add to `backend/types.py` alongside the existing `GRN` type:

```python
@dataclass
class eGRN:
    """Result of enhancer-driven GRN inference (SCENIC+).

    Fields:
        n_eregulons:   Number of eRegulons inferred.
        n_tfs:         Number of unique TFs.
        n_regions:     Number of unique regulatory regions.
        n_target_genes: Number of unique target genes.
        eregulons_key: adata.uns key storing the eRegulon list.
        metadata:      Additional details (thresholds, run params, etc.)
    """
    n_eregulons: int
    n_tfs: int
    n_regions: int
    n_target_genes: int
    eregulons_key: str = "scenicplus_eregulons"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_eregulons": self.n_eregulons,
            "n_tfs": self.n_tfs,
            "n_regions": self.n_regions,
            "n_target_genes": self.n_target_genes,
            "eregulons_key": self.eregulons_key,
            "metadata": self.metadata,
        }
```

`adata.uns["scenicplus_eregulons"]` stores the eRegulon **metadata DataFrame** produced by
`format_egrns()` (Tool 4 Step 6) — **for user inspection only**. Tool 5 scores eRegulons by
loading the full `scplus_obj` from disk (path in `adata.uns["scenicplus_object_path"]`), not by
reading this DataFrame. Key columns in the metadata DataFrame:
```
Region_signature_name   str   "{TF}_(+)_{context}" or "{TF}_(-)_{context}"
Gene_signature_name     str   "{TF}_(+)_{context}" or "{TF}_(-)_{context}"
Region                  str   chr:start-end peak identifiers
Gene                    str   target gene symbol
importance_x_rho        float region→gene importance × rho product
importance              float random forest importance score
rho                     float Spearman rho (sign encodes direction: + activating, - repressing)
```

---

## Tool Specifications

### Tool 1: `atac_topic_pycisTopic`

**Files:**
```
backend/tools/atac/topic/pycisTopic.py
wiki/tools/atac_topic_pycisTopic.md
wiki/packages/pycisTopic.md              (new)
```

**Stage:** `topic_modeling` (new stage — add `wiki/stages/topic_modeling.md`)

**Signature:**
```python
def run(
    adata,
    *,
    n_topics: int | list[int] = 40,
    n_iter: int = 500,
    random_state: int = 555,
    alpha: float = 50.0,
    eta: float = 0.1,
    n_cpu: int = 4,
    force: bool = False,
    tmp_path: Path | None = None,
    output_dir: Path | None = None,
) -> object:
```

**Key implementation notes:**

- **`n_topics` behavior:**
  - Single int: fit one model, proceed.
  - List of ints: fit all models, save all to `output_dir / "topic_models/"`, save evaluation
    plots (log-likelihood, Minmo coherence, Arun_2010 density) to
    `output_dir / "topic_model_selection.pdf"`, then **raise an informative error**:
    ```
    ValueError: Multiple topic models fitted. Inspect
    output_dir/topic_model_selection.pdf and re-run with n_topics=<chosen_value>.
    ```
    Do not auto-select — pycisTopic's automatic coherence-based selection is unreliable in
    production pipelines and requires human inspection. Document this in the wiki.

- Input: `adata.X` must be a raw peak-barcode count matrix (not log-normalized, not TF-IDF).
  Assert this — pycisTopic handles its own normalization internally.

- **Peak name format assertion** — pycisTopic parses genomic coordinates from peak names and
  will silently produce wrong regions if the format is wrong:
  ```python
  assert all(":" in v and "-" in v for v in list(adata.var_names)[:5]), (
      "Peak names must be in 'chr:start-end' format for pycisTopic"
  )
  ```

- **Memory guard:**
  - Warn at `adata.n_obs * adata.n_vars > 5e8` (500M entries, ~50k cells × 10k peaks).
  - Hard stop at `> 2e9` unless `force=True` is passed.

- **`n_topics` wrapping** — `run_cgs_models()` requires `n_topics: list[int]` (never a bare int).
  Always wrap before passing:
  ```python
  n_topics_list = [n_topics] if isinstance(n_topics, int) else list(n_topics)
  ```

- `run_cgs_models()` writes large Gibbs sampling temporary files. Use `tmp_path` for these,
  defaulting to `output_dir / "tmp"` when `output_dir` is set, else `/tmp`.
  Use `run_cgs_models(save_path=str(output_dir / "topic_models"))` for built-in per-model
  saving — this is recommended for large datasets and avoids manual pickling each model.

- **Constructing the CistopicObject** — `create_cistopic_object()` requires a **regions × cells**
  matrix. `adata.X` is cells × peaks (AnnData convention), so it must be transposed:
  ```python
  from pycisTopic.cistopic_class import create_cistopic_object
  import scipy.sparse as sp

  # adata.X is cells × peaks; CistopicObject requires regions × cells
  fragment_matrix = adata.X.T.tocsr() if sp.issparse(adata.X) else adata.X.T

  cisTopic_obj = create_cistopic_object(
      fragment_matrix=fragment_matrix,
      cell_names=list(adata.obs_names),
      region_names=list(adata.var_names),  # must be 'chr:start-end' format
  )
  ```

- **Extract matrices after fitting** using the actual attribute names:
  - `model.cell_topic` → `adata.obsm["X_topic"]` (cell × topic, correct orientation)
  - `model.topic_region.T` → `adata.varm["topic_peak_weights"]` (peak × topic; **must
    transpose** because `model.topic_region` is topic × peak)

- **Serialize the full CistopicObject to disk.** Tool 4 (`multi_grn_scenicplus`) requires the
  complete CistopicObject (not just the extracted matrices) to pass as `cisTopic_obj=` to
  `create_SCENICPLUS_object()`:
  ```python
  import pickle
  cistopic_path = output_dir / "cistopic_object.pkl"
  with open(cistopic_path, "wb") as f:
      pickle.dump(cisTopic_obj, f)
  adata.uns["cistopic_object_path"] = str(cistopic_path)
  ```

- Topic region sets (top peaks per topic) stored in `adata.uns["topic_region_sets"]` as
  `{topic_id: [peak_names]}` where peak names are strings in `chr:start-end` format.
  This is the direct input to `multi_grn_pycistarget` (which converts them to PyRanges).

**Output stored:**
- `adata.obsm["X_topic"]`: cell × topic matrix
- `adata.varm["topic_peak_weights"]`: peak × topic weight matrix (transposed from model)
- `adata.uns["topic_region_sets"]`: `{topic_id: [peak_names]}`
- `adata.uns["cistopic_object_path"]`: str path to pickled CistopicObject (required by Tool 4)
- `adata.uns["pycisTopic_model_path"]`: str path to pickled best LDA model

**Return:** `adata` (augmented in place)

**Wiki frontmatter:**
```yaml
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
```

---

### Tool 2: `multi_grn_pycistarget`

**Files:**
```
backend/tools/multi/grn/pycistarget.py
wiki/tools/multi_grn_pycistarget.md
wiki/packages/pycistarget.md             (new)
```

**Signature:**
```python
def run(
    adata,
    *,
    species: str,                                    # 'homo_sapiens', 'mus_musculus', etc. REQUIRED
    ctx_db_path: str | Path,                         # path to cisTarget ranking .feather db
    dem_db_path: str | Path | None = None,           # path to DEM database (optional; enables DEM)
    motif_annotations_path: str | Path,
    region_sets_key: str = "topic_region_sets",
    ctx_auc_threshold: float = 0.005,
    ctx_nes_threshold: float = 3.0,
    ctx_rank_threshold: float = 0.05,                # fraction of top-ranked regions (NOT an int)
    dem_log2fc_thr: float = 0.5,
    dem_motif_hit_thr: float = 3.0,
    dem_max_bg_regions: int = 500,
    annotation_version: str = "v9",                  # must match downloaded feather database version
    n_cpu: int = 4,
    output_dir: Path | None = None,
) -> object:
```

**Key implementation notes:**

- `run_pycistarget()` lives in `scenicplus.wrappers.run_pycistarget`, not in the pycistarget
  package directly. Import from there:
  ```python
  from scenicplus.wrappers.run_pycistarget import run_pycistarget
  ```

- **`species` is required with no default.** It is used to download TSS annotations from
  biomart (for promoter exclusion). Valid values: `'homo_sapiens'`, `'mus_musculus'`,
  `'drosophila_melanogaster'`, `'gallus_gallus'`.

- **`annotation_version` default is `'v9'`** — this must match the version of the downloaded
  cisTarget feather databases. The existing `pyscenic_databases` resource uses `v10nr_clust`
  databases, so this parameter must be set to `'v10nr_clust'` when using those files. Add a
  cross-reference note in the wiki that the version must match the database files.

- **`ctx_db_path` and `dem_db_path` are separate parameters** (not a unified list). The plan's
  original `cistarget_db_paths` list does not map to this API. `dem_db_path=None` disables DEM;
  pass it to enable DEM for small region sets.

- Input region sets come from `adata.uns[region_sets_key]` (string peak names produced by
  `atac_topic_pycisTopic`). **These must be converted to `pr.PyRanges` before calling
  `run_pycistarget()`** — the function requires `Dict[str, pr.PyRanges]`, not strings:
  ```python
  import pyranges as pr

  def _peaks_to_pyranges(peak_names: list[str]) -> pr.PyRanges:
      """Convert 'chr:start-end' peak strings to a PyRanges object."""
      parts = [p.replace(":", "-").split("-") for p in peak_names]
      return pr.PyRanges(
          chromosomes=[p[0] for p in parts],
          starts=[int(p[1]) for p in parts],
          ends=[int(p[2]) for p in parts],
      )

  region_sets = {
      k: _peaks_to_pyranges(v)
      for k, v in adata.uns[region_sets_key].items()
  }
  ```

- `run_pycistarget()` requires a `save_path` argument (where it writes intermediate files).
  Map `output_dir` to this:
  ```python
  save_path = str(output_dir / "pycistarget")
  ```

- **`path_to_motif_annotations` not `motif_annotations_path`** — the actual parameter name in
  `run_pycistarget()` is `path_to_motif_annotations`. The tool signature uses
  `motif_annotations_path` for user-facing consistency, but must map it correctly in the call:
  ```python
  menr = run_pycistarget(
      region_sets=region_sets,
      species=species,
      save_path=save_path,
      ctx_db_path=str(ctx_db_path),
      dem_db_path=str(dem_db_path) if dem_db_path else None,
      path_to_motif_annotations=str(motif_annotations_path),  # correct param name
      annotation_version=annotation_version,
      ctx_auc_threshold=ctx_auc_threshold,
      ctx_nes_threshold=ctx_nes_threshold,
      ctx_rank_threshold=ctx_rank_threshold,
      dem_log2fc_thr=dem_log2fc_thr,
      dem_motif_hit_thr=dem_motif_hit_thr,
      dem_max_bg_regions=dem_max_bg_regions,
      n_cpu=n_cpu,
  )
  ```

- **DEM background:** when `dem_db_path` is provided, DEM uses all peaks in `adata.var_names`
  as the background set (converted to PyRanges). Do not use random genomic background.

- **Serialize the `menr` dict to disk.** `run_pycistarget()` returns a nested dict
  (`menr: Dict[str, Dict[str, Any]]`). Tool 4's `create_SCENICPLUS_object()` requires this
  dict as `menr=`. Pickle it and store the path:
  ```python
  import pickle
  menr_path = output_dir / "menr.pkl"
  with open(menr_path, "wb") as f:
      pickle.dump(menr, f)
  adata.uns["pycistarget_menr_path"] = str(menr_path)
  ```

- Also extract the summary DataFrame for downstream convenience:
  `adata.uns["pycistarget_tf_region_links"]` — merged TF-region links across all topics.

**Wiki frontmatter:**
```yaml
type: tool
id: multi_grn_pycistarget
modality: multi
stage: grn_inference
backend: backend/tools/multi/grn/pycistarget.py
label: TF-Region Motif Enrichment (pycistarget)
default: false
params:
  species: null           # required — no default
  ctx_auc_threshold: 0.005
  ctx_nes_threshold: 3.0
  ctx_rank_threshold: 0.05
  dem_log2fc_thr: 0.5
  dem_motif_hit_thr: 3.0
  annotation_version: v9
  n_cpu: 4
requires_resources:
  - resource: pyscenic_databases
    params: [ctx_db_path, motif_annotations_path]
    note: Same cisTarget feather databases used by rna_grn_pyscenic. No additional download needed if already present. annotation_version must match the database version (v10nr_clust for the standard preset).
prerequisites:
  - atac_topic_pycisTopic
```

---

### Tool 3: `multi_grn_peak_to_gene`

**Files:**
```
backend/tools/multi/grn/peak_to_gene.py
wiki/tools/multi_grn_peak_to_gene.md
```

No new package file — uses `scenicplus` package (covered by `wiki/packages/scenicplus.md`).

**Signature:**
```python
def run(
    adata,
    *,
    rna_h5ad_path: str | Path,
    gene_annotation: pd.DataFrame | None = None,   # TSS annotation; if None, fetched from biomart
    chromsizes: pd.DataFrame | None = None,         # chr sizes; if None, fetched from biomart
    search_space_upstream: tuple[int, int] = (1_000, 150_000),   # (min, max) bp upstream of TSS
    search_space_downstream: tuple[int, int] = (1_000, 150_000), # (min, max) bp downstream of TSS
    search_space_extend_tss: tuple[int, int] = (10, 10),         # (upstream, downstream) TSS ext
    importance_threshold: float = 0.05,          # post-hoc filter on random forest importance
    rho_threshold: float = 0.03,                 # post-hoc filter on |Spearman rho|
    importance_scoring_method: str = "GBM",      # 'RF', 'ET', or 'GBM'
    n_cpu: int = 4,
    annotation_source: str = "biomart",
    biomart_host: str | None = None,
    gtf_path: str | Path | None = None,
    output_dir: Path | None = None,
) -> object:
```

**Key implementation notes:**

- The SCENIC+ peak-to-gene step is **two separate calls**, not one:

  **Step 1 — Define search space** (candidate peak-gene pairs by genomic distance):
  ```python
  from scenicplus.data_wrangling.gene_search_space import get_search_space

  # get_search_space does NOT take atac_adata — it takes sets of region/gene names
  # plus gene annotation and chromsizes DataFrames
  search_space_df = get_search_space(
      scplus_region=set(adata.var_names),      # peak names (chr:start-end format)
      scplus_genes=set(rna_adata.var_names),   # gene symbols
      gene_annotation=gene_annotation,          # TSS annotation DataFrame
      chromsizes=chromsizes,                    # chromosome sizes DataFrame
      upstream=search_space_upstream,           # tuple (min_bp, max_bp) upstream of TSS
      downstream=search_space_downstream,       # tuple (min_bp, max_bp) downstream of TSS
      extend_tss=search_space_extend_tss,       # tuple (upstream_ext, downstream_ext)
  )
  # Returns DataFrame with columns: Name (region), Gene, Distance
  ```

  **Fetching `gene_annotation` and `chromsizes`:**
  If not provided by the user, fetch via pybiomart. Add a helper:
  ```python
  # gene_annotation: DataFrame with columns Chromosome, Start, Strand, Gene (symbol)
  # chromsizes: DataFrame with columns Chromosome, Start (=0), End (=chr length)
  # These are standard outputs of pyranges_db or pybiomart queries.
  # If gtf_path is provided (offline), parse from GTF instead.
  ```
  Expose `chromsizes_path: str | Path | None = None` as an alternative to biomart for offline use.

  **Step 2 — Compute correlation + importance scores:**
  ```python
  import pandas as pd
  import scipy.sparse as sp
  from scenicplus.enhancer_to_gene import calculate_regions_to_genes_relationships

  # The function requires DataFrames (cells × features), not AnnData objects
  df_acc = pd.DataFrame(
      adata.X.toarray() if sp.issparse(adata.X) else adata.X,
      index=adata.obs_names,
      columns=adata.var_names,
  )
  df_exp = pd.DataFrame(
      rna_adata.X.toarray() if sp.issparse(rna_adata.X) else rna_adata.X,
      index=rna_adata.obs_names,
      columns=rna_adata.var_names,
  )

  r2g_df = calculate_regions_to_genes_relationships(
      df_exp_mtx=df_exp,
      df_acc_mtx=df_acc,
      search_space=search_space_df,
      temp_dir=output_dir / "r2g_tmp",     # required temp directory
      correlation_scoring_method="SR",      # explicit: SR=Spearman (default), PR=Pearson
      importance_scoring_method=importance_scoring_method,
      n_cpu=n_cpu,
  )
  ```

  **Step 3 — Apply thresholds as post-hoc filters** (these are NOT parameters of the function):
  ```python
  # Columns: region, target, importance, rho, importance_x_rho, importance_x_abs_rho, Distance
  r2g_df = r2g_df[
      (r2g_df["importance"] > importance_threshold) &
      (r2g_df["rho"].abs() > rho_threshold)
  ]
  ```

- `importance_threshold` and `rho_threshold` control post-hoc filtering of the returned
  DataFrame — they are **not** parameters of `calculate_regions_to_genes_relationships()`:
  - `importance_threshold`: discard links with random forest importance below this value.
  - `rho_threshold`: discard links where |Spearman rho| is too small to assign direction;
    remaining links with rho > 0 are activating, rho < 0 are repressing.

- **`upstream`/`downstream` are tuples `(min_bp, max_bp)`**, not single ints. The default
  `(1000, 150000)` means: include peaks between 1kb and 150kb from the TSS. The plan's
  previous single-int parameters are exposed as the max values; the min stays at 1000.

- **`chromsizes` is required** by `get_search_space()`. It must be a DataFrame with columns
  `Chromosome` and `End` (chromosome length). Fetch it from UCSC or biomart, or accept a
  `chromsizes_path` pointing to a UCSC-format .chrom.sizes file.

- `correlation_scoring_method="SR"` must be passed **explicitly**. `"SR"` = Spearman,
  `"PR"` = Pearson.

- Output stored in `adata.uns["scenicplus_peak_gene_links"]` — filtered `r2g_df` with columns:
  `region, target, importance, rho, Distance`.
- Do NOT overwrite `adata.uns["peak_gene_links"]` — keep both tools' outputs separate.
- Warn when fewer than 200 cells are present.

**Why separate from existing `atac_peak_to_gene_correlation`:**
The existing tool uses Pearson correlation, no importance scores, no chromsizes, and 500kb
window. Its output schema is incompatible with SCENIC+ eRegulon inference.

**Wiki frontmatter:**
```yaml
type: tool
id: multi_grn_peak_to_gene
modality: multi
stage: grn_inference
backend: backend/tools/multi/grn/peak_to_gene.py
label: Peak-to-Gene Correlation (SCENIC+ style)
default: false
params:
  search_space_upstream: [1000, 150000]
  search_space_downstream: [1000, 150000]
  search_space_extend_tss: [10, 10]
  importance_threshold: 0.05
  rho_threshold: 0.03
  importance_scoring_method: GBM
  n_cpu: 4
prerequisites:
  - atac_peak_calling_macs2 or atac_peak_calling_macs3
```

---

### Tool 4: `multi_grn_scenicplus`

**Files:**
```
backend/tools/multi/grn/scenicplus.py
wiki/tools/multi_grn_scenicplus.md
wiki/packages/scenicplus.md              (new)
```

**Signature:**
```python
def run(
    adata,
    *,
    rna_h5ad_path: str | Path,
    cistopic_object_path: str | Path,        # pickled CistopicObject from atac_topic_pycisTopic
    pycistarget_menr_path: str | Path,       # pickled menr dict from multi_grn_pycistarget
    tf_list_path: str | Path,                # TF names file (allTFs_hg38.txt) for TF→gene step
    coexpression_adj_path: str | Path | None = None,  # path to GRNBoost2 .tsv; if None, re-compute
    peak_gene_links_key: str = "scenicplus_peak_gene_links",
    min_target_genes: int = 10,
    min_regions_per_gene: int = 0,
    rho_threshold: float = 0.05,             # single rho cutoff for activating/repressing split
    rho_dichotomize_tf2g: bool = True,       # split TF→gene by rho sign
    rho_dichotomize_r2g: bool = True,        # split region→gene by rho sign
    rho_dichotomize_eregulon: bool = True,   # split eRegulon by rho sign
    quantiles: tuple = (0.85, 0.90, 0.95),
    top_n_regionTogenes_per_gene: tuple = (5, 10, 15),
    gsea_n_perm: int = 1000,
    run_aucell: bool = True,
    ray_n_cpu: int | None = None,
    output_dir: Path | None = None,
) -> eGRN:
```

**Key implementation notes:**

The full Tool 4 workflow is five sequential steps inside one tool call:

**Step 1 — Construct SCENICPLUS object:**
```python
import pickle
import scanpy as sc
from scenicplus.scenicplus_class import create_SCENICPLUS_object

rna_adata = sc.read_h5ad(rna_h5ad_path)

with open(cistopic_object_path, "rb") as f:
    cisTopic_obj = pickle.load(f)    # full CistopicObject from Tool 1

with open(pycistarget_menr_path, "rb") as f:
    menr = pickle.load(f)            # menr dict from run_pycistarget() in Tool 2

scplus_obj = create_SCENICPLUS_object(
    GEX_anndata=rna_adata,           # AnnData: cells × genes
    cisTopic_obj=cisTopic_obj,       # CistopicObject — NOT adata or ACC matrix directly
    menr=menr,                       # nested dict from run_pycistarget — NOT a DataFrame
    multi_ome_mode=True,             # True = paired RNA+ATAC (same barcodes); False = unpaired
)
```

**Step 2 — Merge cistromes** (converts menr into cistrome AnnDatas stored on scplus_obj):
```python
from scenicplus.cistromes import merge_cistromes
merge_cistromes(scplus_obj)
```
This step is **required** before `build_grn()`. Skipping it will cause `build_grn()` to find
no cistromes and silently produce no eRegulons.

**Step 3 — Load TF→gene adjacencies into scplus_obj:**

Option A — use GRNBoost2 result from Tool M (preferred, avoids recomputation):
```python
import pandas as pd
from scenicplus.TF_to_gene import load_TF2G_adj_from_file

# Write the in-memory adjacency list to a TSV for load_TF2G_adj_from_file
if coexpression_adj_path is not None:
    # If rna_grn_grnboost2 already wrote a parquet/tsv file, use it directly
    load_TF2G_adj_from_file(
        scplus_obj,
        f_adj=str(coexpression_adj_path),
        inplace=True,
        key="TF2G_adj",
    )
```

Option B — re-compute TF→gene within SCENIC+ using GBM (slower, independent of GRNBoost2):
```python
from scenicplus.TF_to_gene import calculate_TFs_to_genes_relationships
calculate_TFs_to_genes_relationships(
    scplus_obj,
    tf_file=str(tf_list_path),
    ray_n_cpu=ray_n_cpu,
    method="GBM",
    _temp_dir=str(output_dir / "tf2g_tmp"),
    key="TF2G_adj",
)
```

**Step 4 — Load region→gene adjacencies into scplus_obj:**
```python
# r2g DataFrame is already in adata.uns from Tool 3 (multi_grn_peak_to_gene)
r2g_df = adata.uns[peak_gene_links_key]  # columns: region, target, importance, rho, Distance
# Key must match region_to_gene_key in build_grn (default "region_to_gene")
scplus_obj.uns["region_to_gene"] = r2g_df
```

**Step 5 — Build eGRN with GSEA:**
```python
from scenicplus.grn_builder.gsea_approach import build_grn

# build_grn takes scplus_obj and accesses all inputs via uns keys.
# Data must already be stored on scplus_obj:
#   adj_key        → scplus_obj.uns["TF2G_adj"]         (from Step 3)
#   region_to_gene_key → scplus_obj.uns["region_to_gene"] (from Step 4)
#   cistromes_key  → scplus_obj.uns["Cistromes"]["Unfiltered"] (from Step 2)
build_grn(
    scplus_obj,
    adj_key="TF2G_adj",
    cistromes_key="Unfiltered",
    region_to_gene_key="region_to_gene",
    min_target_genes=min_target_genes,
    adj_pval_thr=1,
    min_regions_per_gene=min_regions_per_gene,
    quantiles=quantiles,
    top_n_regionTogenes_per_gene=top_n_regionTogenes_per_gene,
    rho_dichotomize_tf2g=rho_dichotomize_tf2g,
    rho_dichotomize_r2g=rho_dichotomize_r2g,
    rho_dichotomize_eregulon=rho_dichotomize_eregulon,
    rho_threshold=rho_threshold,
    merge_eRegulons=True,
    order_regions_to_genes_by="importance",
    order_TFs_to_genes_by="importance",
    key_added="eRegulons",
    ray_n_cpu=ray_n_cpu,
    inplace=True,
)
```

- **`rho_threshold`** (single value): controls activating/repressing split across all layers.
  `rho_dichotomize_tf2g/r2g/eregulon` booleans individually enable the split for each link type.
- **There is no `infer_regulons()` call** — `build_grn()` does the complete eRegulon inference.
- **`ray_n_cpu` not `n_cpu`** — SCENIC+ uses Ray for parallelism.
- **No `_temp_dir` parameter** — not in the public API; `build_grn` manages its own temp storage.

**Step 6 — Convert eRegulon list to metadata DataFrame and signatures:**
```python
from scenicplus.utils import format_egrns
from scenicplus.eregulon_enrichment import get_eRegulons_as_signatures

# build_grn stores List[eRegulon] objects — not a DataFrame.
# format_egrns converts these to a tidy DataFrame with columns:
#   Region_signature_name, Region, Gene_signature_name, Gene,
#   importance_x_rho, importance_x_abs_rho, rho, importance, ...
format_egrns(
    scplus_obj,
    eregulons_key="eRegulons",   # matches key_added in build_grn
    TF2G_key="TF2G_adj",
    key_added="eRegulon_metadata",
)
# Store the metadata DataFrame in adata.uns for user inspection
adata.uns["scenicplus_eregulons"] = scplus_obj.uns["eRegulon_metadata"]

# get_eRegulons_as_signatures is required before score_eRegulons
# converts metadata to signature dicts: {eRegulon_name: [gene/region list]}
get_eRegulons_as_signatures(
    scplus_obj,
    eRegulon_metadata_key="eRegulon_metadata",
    key_added="eRegulon_signatures",
)
```

**Step 7 — Serialize scplus_obj to disk** (required: Tool 5 loads it for re-scoring):
```python
import dill   # SCENIC+ requires dill, not pickle, to serialize SCENICPLUS objects

scplus_obj_path = output_dir / "scplus_obj.pkl"
with open(scplus_obj_path, "wb") as f:
    dill.dump(scplus_obj, f)
adata.uns["scenicplus_object_path"] = str(scplus_obj_path)
```

**GRNBoost2 adjacency path:** `rna_grn_grnboost2` stores adjacencies in `adata.uns` as a list of dicts. If it also wrote a parquet file (check `adata.uns["grnboost2_adj_path"]`), pass that path as `coexpression_adj_path`. Otherwise, write a temp TSV:
```python
adj_df = pd.DataFrame(adata.uns["grnboost2_adjacencies"])
temp_adj_path = output_dir / "grnboost2_adj.tsv"
adj_df.to_csv(temp_adj_path, sep="\t", index=False)
```

If `run_aucell=True`, run AUCell on the inferred eRegulons (see Tool 5 for the scoring logic).

- Output: `adata.uns["scenicplus_eregulons"]` — eRegulon metadata DataFrame produced by `format_egrns()`;
  columns include `Region_signature_name`, `Region`, `Gene_signature_name`, `Gene`, importance metrics.
  This is the format expected by `score_eRegulons()` in Tool 5.

**Validation checks before construction:**
```python
assert peak_gene_links_key in adata.uns, "Run multi_grn_peak_to_gene first"
assert Path(cistopic_object_path).exists(), (
    f"CistopicObject not found at {cistopic_object_path}. Run atac_topic_pycisTopic first."
)
assert Path(pycistarget_menr_path).exists(), (
    f"pycistarget menr dict not found at {pycistarget_menr_path}. Run multi_grn_pycistarget first."
)
```

**Wiki frontmatter:**
```yaml
type: tool
id: multi_grn_scenicplus
modality: multi
stage: grn_inference
backend: backend/tools/multi/grn/scenicplus.py
label: Enhancer-driven eGRN Inference (SCENIC+)
default: false
params:
  min_target_genes: 10
  min_regions_per_gene: 0
  rho_threshold: 0.05
  quantiles: [0.85, 0.90, 0.95]
  top_n_regionTogenes_per_gene: [5, 10, 15]
  gsea_n_perm: 1000
  run_aucell: true
  ray_n_cpu: 4
requires_resources:
  - resource: pyscenic_databases
    note: Same files as rna_grn_pyscenic. tf_list_path needed for TF→gene step.
prerequisites:
  - atac_topic_pycisTopic
  - multi_grn_pycistarget
  - multi_grn_peak_to_gene
  - rna_grn_grnboost2
```

---

### Tool 5: `multi_grn_scenicplus_aucell`

**Files:**
```
backend/tools/multi/grn/scenicplus_aucell.py
wiki/tools/multi_grn_scenicplus_aucell.md
```

**Signature:**
```python
def run(
    adata,
    *,
    eregulons_key: str = "scenicplus_eregulons",
    scplus_obj_key: str = "scenicplus_object_path",  # adata.uns key pointing to dill pickle
    auc_threshold: float = 0.05,
    celltype_key: str | None = None,   # obs column for Regulon Specificity Score (RSS)
    n_cpu: int = 1,
    output_dir: Path | None = None,
) -> eGRN:
```

**Key implementation notes:**

- Requires the full `SCENICPLUS` object (serialized by Tool 4 with `dill`). Load it:
  ```python
  import dill
  from scenicplus.eregulon_enrichment import score_eRegulons, make_rankings, get_eRegulons_as_signatures

  scplus_obj_path = adata.uns[scplus_obj_key]
  with open(scplus_obj_path, "rb") as f:
      scplus_obj = dill.load(f)
  ```

- **Prepare signatures** (may already be present from Tool 4's Step 6 — check first):
  ```python
  if "eRegulon_signatures" not in scplus_obj.uns:
      get_eRegulons_as_signatures(
          scplus_obj,
          eRegulon_metadata_key="eRegulon_metadata",
          key_added="eRegulon_signatures",
      )
  ```

- **Make rankings then score twice** — `score_eRegulons` must be called separately for
  `enrichment_type='region'` and `enrichment_type='gene'`. Both accumulate into the same
  `key_added` key under `scplus_obj.uns`:
  ```python
  region_ranking = make_rankings(scplus_obj, target='region')
  gene_ranking   = make_rankings(scplus_obj, target='gene')

  score_eRegulons(
      scplus_obj,
      ranking=region_ranking,
      eRegulon_signatures_key="eRegulon_signatures",
      key_added="eRegulon_AUC",
      enrichment_type="region",
      auc_threshold=auc_threshold,
      n_cpu=n_cpu,
  )
  score_eRegulons(
      scplus_obj,
      ranking=gene_ranking,
      eRegulon_signatures_key="eRegulon_signatures",
      key_added="eRegulon_AUC",
      enrichment_type="gene",
      auc_threshold=auc_threshold,
      n_cpu=n_cpu,
  )

  # Results accumulate under scplus_obj.uns["eRegulon_AUC"]
  atac_auc_df = scplus_obj.uns["eRegulon_AUC"]["Region_based"]   # DataFrame cells × eRegulons
  rna_auc_df  = scplus_obj.uns["eRegulon_AUC"]["Gene_based"]     # DataFrame cells × eRegulons
  ```

- **obsm must be numpy arrays, not DataFrames.** Extract `.values` before storing:
  ```python
  adata.obsm["X_scenicplus_atac_auc"] = atac_auc_df.values
  adata.obsm["X_scenicplus_rna_auc"]  = rna_auc_df.values
  adata.uns["scenicplus_auc_regulon_names"] = list(rna_auc_df.columns)
  ```
- **Key collision with Tool 4.** If `multi_grn_scenicplus` was run with `run_aucell=True`,
  these same keys already exist. This tool overwrites them intentionally (re-scoring with
  different thresholds). Document in the wiki.
- RSS (Regulon Specificity Score) per cell type: if `celltype_key` is provided and the
  column exists in `adata.obs`, compute RSS and store in `adata.uns["scenicplus_rss"]`.

**When to run separately vs. inside `multi_grn_scenicplus`:**
`multi_grn_scenicplus` runs AUCell internally by default (`run_aucell=True`). This separate
tool re-scores with different thresholds without rerunning eRegulon inference.

**Wiki frontmatter:**
```yaml
type: tool
id: multi_grn_scenicplus_aucell
modality: multi
stage: grn_inference
backend: backend/tools/multi/grn/scenicplus_aucell.py
label: eRegulon AUCell Scoring (SCENIC+)
default: false
params:
  auc_threshold: 0.05
  seed: 42
  n_cpu: 4
prerequisites:
  - multi_grn_scenicplus
```

---

### Tool 6: `rna_grn_pyscenic_aucell` (completing existing SCENIC)

**Files:**
```
backend/tools/rna/grn/pyscenic_aucell.py
wiki/tools/rna_grn_pyscenic_aucell.md
```

**Signature:**
```python
def run(
    adata,
    *,
    regulons_key: str = "pyscenic_regulons",
    auc_threshold: float = 0.05,
    n_cpu: int = 4,
    seed: int = 42,
    output_dir: Path | None = None,
) -> GRN:
```

**Key implementation notes:**

- Reads `adata.uns[regulons_key]` — the `{TF: [target_genes]}` dict from `rna_grn_pyscenic`.
- Converts to `{TF: frozenset(genes)}` for `pyscenic.aucell.aucell()`.
- `aucell()` expects a `(cells × genes)` ranking matrix. Build it from `adata.X`:
  - Dense rank each row (cell), higher expression = lower rank.
  - Use `create_rankings()` from `pyscenic.aucell` if available, otherwise rank manually with
    `scipy.stats.rankdata`.
- **`obsm` stores numpy arrays, not DataFrames.** Extract before storing:
  ```python
  auc_matrix = aucell(...)  # returns DataFrame (cells × TF regulons)
  adata.obsm["X_pyscenic_auc"] = auc_matrix.values          # numpy array
  adata.uns["pyscenic_auc_tf_names"] = list(auc_matrix.columns)  # regulon name index
  ```

**Wiki frontmatter:**
```yaml
type: tool
id: rna_grn_pyscenic_aucell
modality: rna
stage: grn_inference
backend: backend/tools/rna/grn/pyscenic_aucell.py
label: AUCell Regulon Activity Scoring (pySCENIC)
default: false
params:
  auc_threshold: 0.05
  n_cpu: 4
  seed: 42
prerequisites:
  - rna_grn_pyscenic
```

---

## New Wiki Nodes Required

### Stage nodes
- `wiki/stages/topic_modeling.md` — new stage for LDA/NMF topic models on peak matrices
- `wiki/stages/grn_inference.md` — currently missing (stage exists in frontmatter but no file)

### Method nodes
- `wiki/methods/enhancer_grn.md` — eGRN vs. co-expression GRN, three evidence layers,
  pseudoreplication warnings, when to use SCENIC+ over pySCENIC

### Package nodes
- `wiki/packages/pycisTopic.md`
- `wiki/packages/pycistarget.md`
- `wiki/packages/scenicplus.md`

### Updates to existing nodes
- `wiki/methods/coexpression_grn.md` — add `rna_grn_pyscenic_aucell` edge
- `wiki/packages/pyscenic.md` — add AUCell stage description (currently missing)
- `wiki/resources/pyscenic_databases.md` — add note that SCENIC+ uses same databases

---

## Database and Resource Requirements

| Resource | Already exists | Notes |
|---|---|---|
| cisTarget feather databases | Yes — `pyscenic_databases` resource | Shared with pySCENIC. No new download utility. |
| TF list (allTFs_hg38.txt) | Yes — in `pyscenic_databases` | Same file. |
| Motif annotations (.tbl) | Yes — in `pyscenic_databases` | Same file. |
| Gene annotation (biomart/GTF) | No | SCENIC+ uses biomart by default. Support GTF via `gtf_path` for offline use. Not a resource node. |
| Genome FASTA | No new requirement | Not needed — pycistarget uses pre-ranked databases, not sequence scanning. |

No new resource nodes are needed for SCENIC+. The existing `pyscenic_databases` resource
covers everything.

---

## Implementation Order

Steps are ordered by dependency. Steps at the same level are independent and can be
implemented in parallel.

```
Level 0 — Foundation (no prerequisites)
  A. backend/types.py — add eGRN dataclass
  B. wiki/stages/grn_inference.md — missing stage file
  C. wiki/stages/topic_modeling.md — new stage
  D. wiki/methods/enhancer_grn.md — new method node
  E. wiki/packages/pycisTopic.md
  F. wiki/packages/pycistarget.md
  G. wiki/packages/scenicplus.md

Level 1 — Complete existing pySCENIC
  H. rna_grn_pyscenic_aucell (backend + wiki)
  I. Update wiki/packages/pyscenic.md (add AUCell stage)
  J. Update wiki/methods/coexpression_grn.md (add aucell edge)

Level 2 — SCENIC+ prerequisites (independent of each other)
  K. atac_topic_pycisTopic (backend + wiki)
  L. multi_grn_peak_to_gene (backend + wiki)
  M. rna_grn_grnboost2 already done — verify output key compatibility

Level 3 — Depends on K
  N. multi_grn_pycistarget (backend + wiki)

Level 4 — Depends on K, L, M, N
  O. multi_grn_scenicplus (backend + wiki)

Level 5 — Depends on O
  P. multi_grn_scenicplus_aucell (backend + wiki)

Level 6 — Cleanup
  Q. Update wiki/resources/pyscenic_databases.md (add SCENIC+ note)
  R. Update wiki/tasks/ — add task node for eGRN analysis if task graph supports multi-modal GRN
```

Total: 6 backend tool files, 6 wiki tool files, 3 wiki package files, 2 wiki stage files,
1 wiki method file, 1 type addition, 3 wiki updates.

---

## Key Decisions and Caveats

**Pseudoreplication in peak-to-gene correlation.** SCENIC+ requires enough cells per condition
for stable correlations. For datasets with <5 cells per donor, the correlation step will
produce noisy links. The `multi_grn_peak_to_gene` tool should warn when fewer than 200 cells
are present — below that, pseudobulk aggregation before correlation is recommended.

**Memory.** `atac_topic_pycisTopic` loads the full peak × cell matrix. Add guards:
warn at `adata.n_obs * adata.n_vars > 5e8`; hard stop at `> 2e9` with `force: bool = False`.
The original threshold of 5e9 was 10× too high to be practically useful.

**Two artifacts must be serialized to disk across tools:**
- Tool 1 (`atac_topic_pycisTopic`) serializes the full `CistopicObject` to
  `cistopic_object.pkl`. Tool 4 needs it for `create_SCENICPLUS_object(cisTopic_obj=...)`.
- Tool 2 (`multi_grn_pycistarget`) serializes the `menr` dict (returned by `run_pycistarget()`)
  to `menr.pkl`. Tool 4 needs it for `create_SCENICPLUS_object(menr=...)`.
- Both paths are stored in `adata.uns` for downstream tools to locate them.

**Tool 4 five-step workflow.** `multi_grn_scenicplus` is the most complex tool — it orchestrates
five sequential steps that must run in order:
1. `create_SCENICPLUS_object(GEX_anndata, cisTopic_obj, menr, multi_ome_mode=True)`
2. `merge_cistromes(scplus_obj)` — **required before `build_grn()`**; converts menr into cistrome AnnDatas
3. Load TF→gene into scplus_obj via `load_TF2G_adj_from_file()` (preferred) or `calculate_TFs_to_genes_relationships()`
4. Load region→gene DataFrame from `adata.uns[peak_gene_links_key]` into scplus_obj
5. `build_grn(scplus_obj, ...)` — standalone function from `scenicplus.grn_builder.gsea_approach`; **not** a method on scplus_obj

**`build_grn()` parameter notes:**
- First arg is `SCENICPLUS_obj` (positional); all data accessed via uns keys
- `adj_key="TF2G_adj"`: key where TF→gene adj is stored (by `load_TF2G_adj_from_file`)
- `cistromes_key="Unfiltered"`: key where cistromes are stored (by `merge_cistromes`)
- `region_to_gene_key="region_to_gene"`: key where r2g DataFrame is stored
- `rho_threshold` = single float; direction split via `rho_dichotomize_tf2g/r2g/eregulon` booleans
- `ray_n_cpu` not `n_cpu`; **no `_temp_dir` parameter** (not in public API)
- `key_added="eRegulons"` (default); eRegulons stored at `scplus_obj.uns["eRegulons"]`
- `inplace=True` (default): modifies scplus_obj in place
- No `infer_regulons()` call — `build_grn()` is the terminal inference step

**`annotation_version` must match database files.** `run_pycistarget()` default is `'v9'` but
the existing `pyscenic_databases` resource uses `v10nr_clust` feather files. Always set
`annotation_version='v10nr_clust'` when using the standard preset, or the motif annotation
lookup will silently use the wrong version.

**Tool 4 post-build_grn preparation chain (required order):**
1. `format_egrns(scplus_obj, eregulons_key="eRegulons", key_added="eRegulon_metadata")` — converts
   `List[eRegulon]` from `build_grn` into a tidy DataFrame. Stored in `scplus_obj.uns["eRegulon_metadata"]`
   and also copied to `adata.uns["scenicplus_eregulons"]` for user inspection.
2. `get_eRegulons_as_signatures(scplus_obj, eRegulon_metadata_key="eRegulon_metadata", key_added="eRegulon_signatures")` —
   converts metadata DataFrame into signature dicts for `score_eRegulons`.
3. `dill.dump(scplus_obj, ...)` — SCENIC+ objects must be serialized with `dill`, not `pickle`.
   Path stored in `adata.uns["scenicplus_object_path"]` for Tool 5 to find.

**`score_eRegulons` stable API takes `scplus_obj`, not DataFrames.** Tool 5 uses:
- `make_rankings(scplus_obj, target='region')` and `make_rankings(scplus_obj, target='gene')`
  to build `CistopicImputedFeatures` ranking objects
- `score_eRegulons(scplus_obj, ranking=..., enrichment_type='region'|'gene', key_added='eRegulon_AUC', ...)`
  called twice — once per enrichment type
- Results in `scplus_obj.uns["eRegulon_AUC"]["Gene_based"]` and `["Region_based"]` as DataFrames
- Extract `.values` to store in `adata.obsm`

**SCENIC+ internal AUCell and key collision.** `multi_grn_scenicplus` runs AUCell internally
with `run_aucell=True` by default, writing to `adata.obsm["X_scenicplus_rna_auc"]` and
`adata.obsm["X_scenicplus_atac_auc"]`. `multi_grn_scenicplus_aucell` overwrites these when
re-scoring. This is the intended use pattern. Document it explicitly in both wiki pages.

**obsm must be numpy arrays.** AnnData's `.obsm` does not accept DataFrames. All AUCell
output DataFrames must have `.values` extracted before storage, with column names saved
separately in `.uns`.

**cisTarget databases are shared.** The same feather files work for both pySCENIC and
pycistarget. If a user has already downloaded databases for pySCENIC, no additional download
is needed for SCENIC+. Reflect this clearly in all `requires_resources` notes.

**GRNBoost2 output compatibility.** `rna_grn_grnboost2` stores adjacencies in
`adata.uns["grnboost2_adjacencies"]` as a list of dicts. SCENIC+ `build_grn()` expects a
DataFrame with columns `[TF, target, importance]`. The `multi_grn_scenicplus` tool must convert:
```python
adj_df = pd.DataFrame(adata.uns[coexpression_key])
```
This is trivial but must be present in the implementation.
