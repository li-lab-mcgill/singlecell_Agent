# MultiVelo Integration Plan

> **Goal:** Add RNA velocity and multi-omic (chromatin + RNA) velocity as a new `velocity` stage
> across two modalities — `rna/velocity/` for scVelo (RNA-only baseline) and `multi/velocity/`
> for MultiVelo (ATAC + RNA). All tools follow existing singlecell_Agent conventions exactly.

---

## 1. Background & Scientific Context

[MultiVelo](https://github.com/welch-lab/MultiVelo) (Li et al., *Nat Biotechnol* 2023) extends
RNA velocity to paired single-cell multiome data (10X Chromium ARC). It models chromatin
accessibility (ATAC) as the upstream driver of transcription, solving a 3-ODE system:

```
dc/dt = α_c(1 − c) − (scale_cc × α_c × c)     [chromatin opening]
du/dt = α × c − β × u                           [unspliced RNA]
ds/dt = β × u − γ × s                           [spliced RNA]
```

Two gene-level models are inferred:
- **Model 1**: Chromatin and transcription are coupled (one switch time t_sw)
- **Model 2**: Decoupled — chromatin opens before transcription begins (three switch times)

**scVelo** (Bergen et al., *Nat Biotechnol* 2020) is the standard RNA-only velocity tool. It
serves as the natural baseline: it uses only `Mu`/`Ms` layers (unspliced/spliced counts from
velocyto) and fits per-gene kinetics with the same ODE system sans chromatin.

---

## 2. Data Requirements & Prerequisites (External to Agent)

Before any velocity tool runs, the user must have prepared:

| Data | Source | Layer / Key |
|------|--------|-------------|
| Spliced RNA counts | velocyto (re-loom from 10X BAM) | `adata.layers["Ms"]` |
| Unspliced RNA counts | velocyto | `adata.layers["Mu"]` |
| ATAC peak matrix | 10X Cell Ranger ARC → MTX | separate h5ad, `adata_atac.X` |
| Peak annotations | Cell Ranger ARC → `atac_peak_annotation.tsv` | file path |
| Feature linkages | Cell Ranger ARC → `feature_linkage.bedpe` | file path |
| WNN neighbors | `multi_embed_wnn` tool | `adata.obsp["connectivities/distances"]` |

The agent should communicate these prerequisites clearly in its planning stage.

---

## 3. Architecture Fit Analysis

### 3.1 Dual-AnnData Convention (Already Established)

The existing system already handles two AnnData objects via `adata.uns["atac_h5ad_path"]`:

- `multi_qc_intersect` → aligns RNA + ATAC, sets `adata.uns["atac_h5ad_path"]`
- `multi_embed_wnn` → reads ATAC from that path, propagates the key
- **MultiVelo tools follow the same pattern exactly** — load ATAC from
  `adata.uns["atac_h5ad_path"]`, modify it in place, save it back

### 3.2 WNN Integration

The existing `multi_embed_wnn` tool stores WNN neighbors in:
- `adata.obsp["connectivities"]` — sparse CSR matrix (cells × cells)
- `adata.obsp["distances"]` — sparse CSR matrix (cells × cells)
- `adata.uns["neighbors"]["params"]["n_neighbors"]` — k value

MultiVelo's `knn_smooth_chrom` requires dense `nn_idx` (cells × k) and `nn_dist` (cells × k)
arrays. The `multi_velocity_knn_smooth` tool extracts these from the sparse obsp matrices via
a sparse-aware row-by-row extraction (see §6.3). **No changes to the WNN tool needed.**

### 3.3 New Stage: `velocity`

Following existing naming conventions:
```
backend/tools/rna/velocity/        rna_velocity_{method}
backend/tools/multi/velocity/      multi_velocity_{method}
```

This mirrors how `embed`, `cluster`, `project`, `grn` are organized.

---

## 4. New Dataclasses

Add to [backend/types.py](../backend/types.py):

### `VelocityResult` — returned by fitting tools

```python
@dataclass
class VelocityResult:
    """Result of RNA or multi-omic velocity fitting.

    Fields:
        method:              "scvelo" or "multivelo"
        n_velocity_genes:    Number of genes used to compute velocity
        velocity_key:        Primary velocity layer in adata (e.g. "velocity" or "velo_s")
        latent_time_key:     adata.obs key for latent time, None if not yet computed
        model_distribution:  {"1": N, "2": M} for multivelo; {} for scvelo
        mean_likelihood:     Mean per-gene fit likelihood
        params_path:         Optional path to saved gene-level parameter table (parquet)
        metadata:            Additional run parameters (max_iter, init_mode, etc.)
    """
    method: str
    n_velocity_genes: int
    velocity_key: str
    latent_time_key: Optional[str] = None
    model_distribution: Dict[str, int] = field(default_factory=dict)
    mean_likelihood: float = 0.0
    params_path: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "n_velocity_genes": self.n_velocity_genes,
            "velocity_key": self.velocity_key,
            "latent_time_key": self.latent_time_key,
            "model_distribution": self.model_distribution,
            "mean_likelihood": self.mean_likelihood,
            "params_path": _path_to_str(self.params_path),
            "metadata": self.metadata,
        }
```

### `VelocityDownstreamResult` — returned by `multi_velocity_downstream`

```python
@dataclass
class VelocityDownstreamResult:
    """Result of velocity graph + latent time + optional LRT computation.

    Fields:
        velocity_key:            Velocity layer used to build the graph
        n_velocity_genes_graph:  Genes included in velocity graph
        latent_time_key:         adata.obs key for latent time; None if not computed
        lrt_n_decoupled:         Genes with decoupled epigenome-transcriptome dynamics
        lrt_n_coupled:           Genes with coupled dynamics
        metadata:                Additional details
    """
    velocity_key: str
    n_velocity_genes_graph: int
    latent_time_key: Optional[str] = None
    lrt_n_decoupled: Optional[int] = None
    lrt_n_coupled: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "velocity_key": self.velocity_key,
            "n_velocity_genes_graph": self.n_velocity_genes_graph,
            "latent_time_key": self.latent_time_key,
            "lrt_n_decoupled": self.lrt_n_decoupled,
            "lrt_n_coupled": self.lrt_n_coupled,
            "metadata": self.metadata,
        }
```

### `LRTResult` — returned by `multi_velocity_lrt`

```python
@dataclass
class LRTResult:
    """Result of epigenome–transcriptome decoupling LRT (mv.LRT_decoupling).

    Fields:
        n_genes_tested:  Total genes tested
        n_decoupled:     Genes where chromatin opens before transcription (pval_c < threshold)
        n_coupled:       Genes where chromatin and transcription are coupled
        pct_decoupled:   Percentage of tested genes that are decoupled
        lrt_table_path:  Path to saved per-gene LRT statistics parquet
        metadata:        Threshold and run parameters
    """
    n_genes_tested: int
    n_decoupled: int
    n_coupled: int
    pct_decoupled: float
    lrt_table_path: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_genes_tested": self.n_genes_tested,
            "n_decoupled": self.n_decoupled,
            "n_coupled": self.n_coupled,
            "pct_decoupled": self.pct_decoupled,
            "lrt_table_path": _path_to_str(self.lrt_table_path),
            "metadata": self.metadata,
        }
```

---

## 5. `adata.uns["velocity"]` Schema (for Auto-Wiring)

All velocity tools write to a consistent `adata.uns["velocity"]` dict. The executor
auto-wires `velocity_key` and `latent_time_key` to downstream tools (same as `embedding.obsm_key`):

```python
adata.uns["velocity"] = {
    "method":          "multivelo",                    # or "scvelo"
    "velocity_key":    "velo_s",                       # primary layer; "velocity" for scvelo
    "velocity_keys":   ["velo_s", "velo_u", "velo_chrom"],  # all layers (multivelo only)
    "latent_time_key": None,                           # set by multi_velocity_downstream
    "n_velocity_genes": 412,
    "fit_complete":    True,
}
```

---

## 6. Tool Inventory

### 6.1 `rna/velocity/scvelo.py` — RNA-Only Baseline (scVelo)

**Tool ID:** `rna_velocity_scvelo`

**Purpose:** Standard dynamical RNA velocity using scVelo. Fits unspliced/spliced kinetics
per gene. Use as a baseline before multi-omic analysis, or when ATAC is unavailable.

**Signature:**
```python
def run(
    adata,
    *,
    embedding_key: str = "X_pca",     # auto-wired from adata.uns["embedding"]["obsm_key"]
    min_shared_counts: int = 20,
    n_pcs: int = 30,
    n_neighbors: int = 30,
    mode: str = "dynamical",          # "dynamical" | "stochastic" | "deterministic"
    compute_latent_time: bool = True,
    output_dir: Path | None = None,
) -> VelocityResult:
```

**Prerequisites:**
- `adata.layers["Mu"]` and `adata.layers["Ms"]` (from velocyto)
- HVG selection already performed by an upstream `rna_feature_selection_*` tool
  (e.g. `rna_feature_selection_scanpy_hvg`). Do not re-run HVG inside this tool.
  Note: scVelo fits velocity on **all genes** that pass `filter_and_normalize` (sufficient
  shared spliced/unspliced counts), not just HVGs. `moments(use_highly_variable=True)` —
  the default — uses `adata.var["highly_variable"]` only for its internal PCA neighbor
  computation, not to restrict which genes have moments or velocity computed. If X_pca is
  already present (passed via `use_rep`), the `highly_variable` flag is entirely bypassed.
  Emit a `UserWarning` if `highly_variable` is absent so the user knows the upstream step
  was skipped, but do not fail — `filter_and_normalize` already does its own gene filtering.
- `adata.obsm[embedding_key]` must exist (default `"X_pca"`, auto-wired from the upstream
  `rna_embed_pca` step via `adata.uns["embedding"]["obsm_key"]`). This follows the same
  pattern as `rna_cluster_leiden` and `rna_project_umap` which also take `embedding_key`.
- **scVelo ≥ 0.4.0 deprecation:** automatic neighbor computation inside `moments()` is
  deprecated. The recommended approach is to pre-compute neighbors explicitly with
  `sc.pp.neighbors()` before calling `moments()`. If neighbors already exist and
  `get_n_neighs(adata) >= n_neighbors`, `moments()` uses the existing graph from
  `adata.obsp["connectivities"]` without recomputing. The tool must therefore compute
  neighbors explicitly to avoid DeprecationWarnings and to control `use_rep`.

**Steps inside `run()`:**
1. `scv.pp.filter_and_normalize(adata, min_shared_counts=min_shared_counts)`
   — velocity-specific gene filtering (genes with sufficient shared spliced/unspliced counts)
   and normalization. This is distinct from HVG selection and must always run.
   ```python
   if "highly_variable" not in adata.var:
       import warnings
       warnings.warn(
           "adata.var['highly_variable'] not found. Run rna_feature_selection_scanpy_hvg "
           "first for best results. Continuing with all genes.",
           UserWarning,
       )
   ```
2. Pre-compute neighbors explicitly using `embedding_key` (matches the pattern of
   `rna_cluster_leiden` / `rna_project_umap`; avoids the scvelo 0.4.0 DeprecationWarning):
   ```python
   import scanpy as sc
   if embedding_key not in adata.obsm:
       raise ValueError(
           f"Embedding '{embedding_key}' not found in adata.obsm. "
           f"Run rna_embed_pca first. Available: {list(adata.obsm.keys())}"
       )
   sc.pp.neighbors(adata, n_neighbors=n_neighbors, n_pcs=n_pcs, use_rep=embedding_key)
   scv.pp.moments(adata)   # uses the pre-computed neighbor graph; no internal recomputation
   ```
   — computes velocity moments on all genes passing step 1
3. `scv.tl.recover_dynamics(adata)` if `mode == "dynamical"`
4. `scv.tl.velocity(adata, mode=mode)`
5. `scv.tl.velocity_graph(adata)`
6. `scv.tl.latent_time(adata)` if `compute_latent_time`
7. Extract `n_velocity_genes` from `adata.var["velocity_genes"].sum()`,
   `mean_likelihood` from `adata.var["fit_likelihood"].mean(skipna=True)`
8. Optionally save gene params to `output_dir/scvelo_gene_params.parquet`
9. Write `adata.uns["velocity"]`
10. Return `VelocityResult`

**adata.uns written:**
```python
# Tool-specific metadata (mirrors adata.uns["wnn"], adata.uns["multivi"], etc.)
adata.uns["scvelo"] = {
    "mode": mode,
    "n_top_genes": n_velocity_genes,
    "min_shared_counts": min_shared_counts,
    "n_pcs": n_pcs,
    "n_neighbors": n_neighbors,
    "embedding_key": embedding_key,
    "mean_likelihood": mean_likelihood,
}
# Auto-wiring key (read by executor and downstream tools)
adata.uns["velocity"] = {
    "method": "scvelo",
    "velocity_key": "velocity",
    "velocity_keys": ["velocity"],
    "latent_time_key": "latent_time" if compute_latent_time else None,
    "n_velocity_genes": n_velocity_genes,
    "fit_complete": True,
}
```

---

### 6.2 `multi/velocity/aggregate_peaks.py` — ATAC Peak → Gene Aggregation

**Tool ID:** `multi_velocity_aggregate_peaks`

**Purpose:** Aggregates 10X peak-level ATAC counts to gene-level accessibility using
MultiVelo's `aggregate_peaks_10x`, then applies TF-IDF normalization. Transforms the ATAC
AnnData from peak space to gene space (shared with RNA var_names).

**Signature:**
```python
def run(
    adata,
    *,
    atac_h5ad_path: str | Path | None = None,
    peaks_annot_path: str | Path,      # atac_peak_annotation.tsv from Cell Ranger ARC
    linkage_path: str | Path,          # feature_linkage.bedpe from Cell Ranger ARC
    use_gene_id: bool = False,         # True if var_names are Ensembl IDs, False for symbols
    tfidf_scale_factor: float = 1e4,
    output_dir: Path | None = None,
) -> object:
```

**Prerequisites:**
- `adata.uns["atac_h5ad_path"]` (set by `multi_qc_intersect`)
- ATAC AnnData must have peaks as var_names (e.g. `chr1:1000-2000`)

**Steps inside `run()`:**
1. Resolve ATAC path from param or `adata.uns["atac_h5ad_path"]`; raise
   `FileNotFoundError` if missing
2. Load ATAC adata
3. `mv.aggregate_peaks_10x(adata_atac, peaks_annot, linkage, use_gene_id=use_gene_id)`
   — converts ATAC from peak space to gene space; result has gene var_names
4. Intersect gene var_names between RNA and gene-level ATAC; raise if no overlap
5. `mv.tfidf_norm(adata_atac, scale_factor=tfidf_scale_factor)`
   — normalizes raw accessibility; stores `Mc` layer
6. Save updated ATAC adata back to same path
7. Write `adata.uns["velocity_preprocess"]` metadata
8. Return adata

**adata.uns written:**
```python
# Tool-specific key — one key per tool, mirrors adata.uns["qc"], adata.uns["wnn"], etc.
adata.uns["velocity_aggregate_peaks"] = {
    "n_atac_genes_before": n_atac_genes_before,
    "n_shared_genes": n_shared,
    "tfidf_applied": True,
    "tfidf_scale_factor": tfidf_scale_factor,
}
```

**Note:** After this tool, `adata_atac.layers["Mc"]` contains TF-IDF normalized
gene-level accessibility. This is the chromatin layer read by `recover_dynamics_chrom`.

---

### 6.3 `multi/velocity/knn_smooth.py` — KNN Chromatin Smoothing

**Tool ID:** `multi_velocity_knn_smooth`

**Purpose:** Smooths raw chromatin accessibility in ATAC using KNN neighbors from the
WNN graph. Required before `recover_dynamics_chrom` because raw peak aggregation is sparse
and noisy. Reuses the WNN neighbor graph already computed by `multi_embed_wnn`.

**Signature:**
```python
def run(
    adata,
    *,
    atac_h5ad_path: str | Path | None = None,
    n_neighbors: int | None = None,    # if None, inferred from adata.uns["neighbors"]
    output_dir: Path | None = None,
) -> object:
```

**Prerequisites:**
- `adata.obsp["distances"]` (sparse CSR, from `multi_embed_wnn`)
- `adata.uns["atac_h5ad_path"]` (pointing to gene-level ATAC after aggregate_peaks)
- ATAC must have `Mc` layer (from `multi_velocity_aggregate_peaks`)

**Steps inside `run()`:**
1. Resolve `k` — check in priority order: explicit param → `adata.uns["wnn"]["n_neighbors"]`
   (written by `multi_embed_wnn`) → `adata.uns["neighbors"]["params"]["n_neighbors"]`
   (written by `sc.pp.neighbors` if used instead of WNN):
   ```python
   k = (
       n_neighbors
       or adata.uns.get("wnn", {}).get("n_neighbors")
       or adata.uns.get("neighbors", {}).get("params", {}).get("n_neighbors")
   )
   if k is None:
       raise ValueError(
           "Could not determine n_neighbors. Run multi_embed_wnn first "
           "or pass n_neighbors explicitly."
       )
   k = int(k)
   ```
2. Extract `nn_idx` (cells × k) and `nn_dist` (cells × k) from sparse distances matrix
   using a **sparse-aware row-by-row extraction** (see below)
3. Load ATAC adata
4. `mv.knn_smooth_chrom(adata_atac, nn_idx, nn_dist)` — smooths `adata_atac.layers["Mc"]`
5. Save updated ATAC adata back
6. Write tool-specific key (one key per tool, consistent with existing convention):
   ```python
   adata.uns["velocity_knn_smooth"] = {
       "n_neighbors": k,
       "source": "wnn" if "wnn" in adata.uns else "neighbors",
   }
   ```
7. Return adata

**Sparse-aware KNN extraction (correct implementation):**

The distances matrix `adata.obsp["distances"]` is a sparse CSR where only the k actual
neighbors have nonzero entries. Do NOT call `.toarray()` — this materializes a dense
`(n_cells × n_cells)` matrix which will OOM on any real dataset (e.g. 50k cells = ~20 GB).
Do NOT use `np.argsort` on the dense array — zeros fill all non-neighbor positions and
would be sorted first, returning non-neighbor indices instead of actual neighbors.

```python
import numpy as np

D = adata.obsp["distances"]   # sparse CSR, already nonzero only for real neighbors
n_cells = D.shape[0]
nn_idx  = np.zeros((n_cells, k), dtype=int)
nn_dist = np.zeros((n_cells, k), dtype=float)

for i in range(n_cells):
    row     = D.getrow(i)
    nz_idx  = row.indices          # column indices of actual neighbors
    nz_dist = row.data             # their distances
    order   = np.argsort(nz_dist)[:k]
    n       = len(order)
    nn_idx[i,  :n] = nz_idx[order]
    nn_dist[i, :n] = nz_dist[order]
```

For very large datasets (>100k cells), the inner loop can be parallelized or vectorized
using `D.tocsr()` + `np.split` on `D.data`/`D.indices`/`D.indptr`.

---

### 6.4 `multi/velocity/recover_dynamics.py` — MultiVelo Core Fitting

**Tool ID:** `multi_velocity_recover_dynamics`

**Purpose:** Runs the central MultiVelo analysis: fits the 3-ODE dynamical model to each
gene, estimating chromatin opening/transcription/splicing/degradation rates and switch
times. This is the computational core (parallelized across genes).

**Confirmed signature of `mv.recover_dynamics_chrom()` (from source):**
```python
mv.recover_dynamics_chrom(
    adata_rna, adata_atac=None, gene_list=None,
    max_iter=5, init_mode='invert', device="cpu",
    neural_net=False, adam=False,
    adam_lr=None, adam_beta1=None, adam_beta2=None, batch_size=None,
    model_to_run=None, plot=False, parallel=True, n_jobs=None,
    save_plot=False, plot_dir=None, rna_only=False, fit=True,
    fit_decoupling=True, extra_color_key=None, embedding='X_umap',
    n_anchors=500, k_dist=1, thresh_multiplier=1.0, weight_c=0.6,
    outlier=99.8, n_pcs=30, n_neighbors=30,
    fig_size=(8, 6), point_size=7, partial=None, direction=None,
    rescale_u=None, alpha=None, beta=None, gamma=None, t_sw=None
)
```

All parameters in the tool signature below are confirmed valid upstream params.

**Tool Signature:**
```python
def run(
    adata,
    *,
    atac_h5ad_path: str | Path | None = None,
    max_iter: int = 5,
    init_mode: str = "invert",         # "invert" | "grid" | "simple"
    model_to_run: int | None = None,   # None = auto-detect; 1 or 2 = force model
    fit_decoupling: bool = True,       # Distinguish Model 1 vs Model 2
    neural_net: bool = False,
    adam: bool = False,
    n_anchors: int = 500,
    weight_c: float = 0.6,             # Weight for chromatin in 3D distance
    n_pcs: int = 30,
    n_neighbors: int = 30,
    likelihood_lower: float = 0.05,    # Min likelihood for velocity gene selection (post-fit)
    parallel: bool = True,
    n_jobs: int | None = None,         # None = os.cpu_count() in MultiVelo; NOT joblib convention
    output_dir: Path | None = None,
) -> VelocityResult:
```

**Note on removed params:** `extra_color_key` and `save_plot` are valid upstream params
but are visualization concerns — they do not affect the fitted model. Omit them from the
tool; a separate `multi_velocity_plot` tool can be added later if needed.

**Prerequisites:**
- `adata.layers["Mu"]` and `adata.layers["Ms"]` (from velocyto)
- `adata.obsp["connectivities"]` (from `multi_embed_wnn`)
- `adata.uns["atac_h5ad_path"]` (ATAC with KNN-smoothed `Mc` layer)
- All cells must be aligned between RNA and ATAC adata

**Steps inside `run()`:**
1. Validate prerequisites; raise informative errors with what was found vs needed
2. Resolve ATAC path; load adata_atac
3. Validate gene overlap between RNA and ATAC var_names
4. Call `mv.recover_dynamics_chrom(adata, adata_atac, max_iter=max_iter,
   init_mode=init_mode, model_to_run=model_to_run, fit_decoupling=fit_decoupling,
   neural_net=neural_net, adam=adam, n_anchors=n_anchors, weight_c=weight_c,
   n_pcs=n_pcs, n_neighbors=n_neighbors, parallel=parallel, n_jobs=n_jobs)`
5. Call `mv.set_velocity_genes(adata, likelihood_lower=likelihood_lower)`
   to flag velocity genes in `adata.var["velo_s_genes"]` / `adata.var["velo_chrom_genes"]`
   **Note on `n_jobs`:** MultiVelo's internal guard treats `n_jobs=None` as `os.cpu_count()`
   (all CPUs). This differs from joblib where `None` means 1 CPU. Do NOT change to `-1`;
   both `None` and `-1` are handled equivalently in MultiVelo, but `None` is the upstream
   default and should be preserved.
6. If `output_dir`: save gene parameter table to `multivelo_gene_params.parquet`
7. Extract result statistics:
   - `n_velocity_genes` from `adata.var["velo_s_genes"].sum()`
   - `model_distribution` from `adata.var["fit_model"].value_counts().to_dict()`
   - `mean_likelihood` from `adata.var.loc[mask, "fit_likelihood"].mean()`
8. Write tool-specific key AND auto-wiring key:
   ```python
   # Tool-specific metadata
   adata.uns["multivelo"] = {
       "max_iter": max_iter,
       "init_mode": init_mode,
       "model_to_run": model_to_run,
       "fit_decoupling": fit_decoupling,
       "n_anchors": n_anchors,
       "weight_c": weight_c,
       "likelihood_lower": likelihood_lower,
       "mean_likelihood": float(mean_likelihood),
       "model_distribution": model_distribution,
   }
   # Auto-wiring key
   adata.uns["velocity"] = {
       "method": "multivelo",
       "velocity_key": "velo_s",
       "velocity_keys": ["velo_s", "velo_u", "velo_chrom"],
       "latent_time_key": None,
       "n_velocity_genes": n_velocity_genes,
       "fit_complete": True,
   }
   ```
9. Save updated ATAC adata back
10. Return:
    ```python
    return VelocityResult(
        method="multivelo",
        n_velocity_genes=n_velocity_genes,
        velocity_key="velo_s",
        latent_time_key=None,
        model_distribution=model_distribution,
        mean_likelihood=float(mean_likelihood),
        params_path=params_path,
        metadata={"max_iter": max_iter, "init_mode": init_mode,
                  "fit_decoupling": fit_decoupling, "weight_c": weight_c},
    )
    ```

**Confirmed `adata.var` columns written by `recover_dynamics_chrom()` (from source):**

| Column | Description |
|--------|-------------|
| `fit_alpha_c` | Chromatin opening rate |
| `fit_alpha` | Transcription rate |
| `fit_beta` | Splicing rate |
| `fit_gamma` | Degradation rate |
| `fit_t_sw1/2/3` | Switch time points |
| `fit_scale_cc`, `fit_rescale_c`, `fit_rescale_u` | Scaling factors |
| `fit_alignment_scaling` | Time range normalization |
| `fit_model` | Assigned model (1 or 2) |
| `fit_direction` | Trajectory direction: `'on'`/`'off'`/`'complete'` |
| `fit_loss` | Optimization loss |
| `fit_likelihood` | Per-gene fit likelihood |
| `fit_likelihood_c` | Chromatin-specific likelihood |
| `fit_ssd_c`, `fit_var_c` | Chromatin residual statistics |
| `fit_c0`, `fit_u0`, `fit_s0` | Initial values (when `fit=True`) |
| `fit_anchor_min_idx`, `fit_anchor_max_idx` | Time range coverage |
| `fit_anchor_velo_min_idx`, `fit_anchor_velo_max_idx` | Velocity anchor range |

**`adata.layers` written:** `fit_t` (gene-specific time per cell), `fit_state` (cell state 0–3),
`velo_s`, `velo_u`, `velo_chrom` (velocity predictions)

**adata.uns written:**
```python
adata.uns["velocity"] = {
    "method": "multivelo",
    "velocity_key": "velo_s",
    "velocity_keys": ["velo_s", "velo_u", "velo_chrom"],
    "latent_time_key": None,          # set by multi_velocity_downstream
    "n_velocity_genes": n_genes,
    "fit_complete": True,
}
```

**Computational note:** For a typical dataset (5k cells, 2k genes), expect 30–90 min
runtime with `parallel=True`. The executor's caching layer will avoid re-running if
input_sha + params are unchanged.

---

### 6.5 `multi/velocity/downstream.py` — Velocity Graph + Latent Time

**Tool ID:** `multi_velocity_downstream`

**Purpose:** Post-fitting steps: computes the velocity transition probability graph,
infers global pseudotime (latent time), and optionally runs the epigenome-transcriptome
coupling LRT. These are fast and may be re-run with different parameters without
re-running the expensive fitting step.

**Confirmed upstream signatures (from source):**
```python
mv.velocity_graph(adata, vkey='velo_s', xkey='Ms', **kwargs)   # vkey IS valid
mv.latent_time(adata, vkey='velo_s', **kwargs)                 # no root_key param
mv.LRT_decoupling(adata_rna, adata_atac, **kwargs)             # requires TWO AnnData
```

**Tool Signature:**
```python
def run(
    adata,
    *,
    atac_h5ad_path: str | Path | None = None,  # required if run_lrt=True
    velocity_key: str | None = None,   # if None, read from adata.uns["velocity"]["velocity_key"]
    compute_latent_time: bool = True,
    run_lrt: bool = False,
    lrt_pval_threshold: float = 0.05,  # p-value cutoff for decoupled/coupled classification
    output_dir: Path | None = None,
) -> VelocityDownstreamResult:
```

**Prerequisites:**
- Velocity layers in adata (from `multi_velocity_recover_dynamics` or `rna_velocity_scvelo`)
- `adata.uns["velocity"]["velocity_key"]` (auto-wired by executor)
- `adata.uns["atac_h5ad_path"]` if `run_lrt=True`

**Steps inside `run()`:**
1. Resolve `vkey` from param or `adata.uns["velocity"]["velocity_key"]`;
   raise `ValueError` if neither is set
2. `mv.velocity_graph(adata, vkey=vkey)` — builds transition probability graph
3. If `compute_latent_time`:
   ```python
   mv.latent_time(adata, vkey=vkey)   # writes adata.obs["latent_time"]
   latent_time_key = "latent_time"
   adata.uns["velocity"]["latent_time_key"] = latent_time_key
   ```
4. If `run_lrt`:
   - Resolve and load adata_atac from `atac_h5ad_path` or `adata.uns["atac_h5ad_path"]`
   - **Warning: `LRT_decoupling` is extremely expensive** — it calls `recover_dynamics_chrom`
     twice internally (with and without `fit_decoupling`), effectively doubling the fitting
     cost. Expect 1–3 hours on a typical dataset. `run_lrt=False` is the default for this reason.
   - Capture all three return values (function does NOT modify adata in-place):
     ```python
     _, _, lrt_df = mv.LRT_decoupling(adata, adata_atac)
     # lrt_df columns: likelihood_c_w_decoupled, likelihood_c_wo_decoupled,
     #                 LRT_c, pval_c, likelihood_w_decoupled, likelihood_wo_decoupled,
     #                 LRT, pval  (index = shared gene names)
     adata.uns["lrt_decoupling"] = lrt_df.to_dict()
     n_decoupled = int((lrt_df["pval_c"] < lrt_pval_threshold).sum())
     n_coupled   = int((lrt_df["pval_c"] >= lrt_pval_threshold).sum())
     if output_dir:
         lrt_df.to_parquet(output_dir / "lrt_decoupling.parquet")
     ```
5. Construct and return result:
   ```python
   # n_velocity_genes_graph: read from the velo_s_genes flag set by set_velocity_genes()
   # in the upstream recover_dynamics step; default to 0 if absent
   import pandas as pd
   n_velocity_genes_graph = int(
       adata.var.get("velo_s_genes", pd.Series(dtype=bool)).sum()
   )

   return VelocityDownstreamResult(
       velocity_key=vkey,
       n_velocity_genes_graph=n_velocity_genes_graph,
       latent_time_key="latent_time" if compute_latent_time else None,
       lrt_n_decoupled=n_decoupled if run_lrt else None,
       lrt_n_coupled=n_coupled if run_lrt else None,
       metadata={"lrt_pval_threshold": lrt_pval_threshold if run_lrt else None},
   )
   ```

**Returns:** `VelocityDownstreamResult` (typed dataclass, consistent with registry conventions)

---

### 6.6 `multi/velocity/lrt_decoupling.py` — Epigenome–Transcriptome Coupling Test

**Tool ID:** `multi_velocity_lrt`

**Purpose:** Standalone wrapper for `mv.LRT_decoupling`. Tests per-gene whether chromatin
accessibility is significantly coupled to transcription (Model 1) vs decoupled (Model 2).
Provides a quantitative measure of epigenome–transcriptome coordination.

**Confirmed upstream signature (from source):**
```python
mv.LRT_decoupling(adata_rna, adata_atac, **kwargs)   # requires BOTH AnnData objects
```

**Tool Signature:**
```python
def run(
    adata,
    *,
    atac_h5ad_path: str | Path | None = None,  # fallback to adata.uns["atac_h5ad_path"]
    lrt_pval_threshold: float = 0.05,
    output_dir: Path | None = None,
) -> LRTResult:
```

**Prerequisites:**
- `adata.var["fit_model"]`, `adata.var["fit_likelihood"]`, `adata.var["fit_likelihood_c"]`
  (all confirmed written by `multi_velocity_recover_dynamics`)
- ATAC AnnData accessible via `atac_h5ad_path` or `adata.uns["atac_h5ad_path"]`

**Steps inside `run()`:**
1. Resolve ATAC path from param or `adata.uns.get("atac_h5ad_path")`; raise
   `ValueError` if neither is set with a message pointing to `multi_qc_intersect`
2. Load adata_atac
3. **Warning: `LRT_decoupling` calls `recover_dynamics_chrom` twice internally**
   (once with `fit_decoupling=True`, once with `False`). This is 2× the cost of
   `multi_velocity_recover_dynamics`. Plan for 1–3 hours on a typical dataset.
4. Capture all three return values — function does NOT modify adata in-place:
   ```python
   _, _, lrt_df = mv.LRT_decoupling(adata, adata_atac)
   # lrt_df columns: likelihood_c_w_decoupled, likelihood_c_wo_decoupled,
   #                 LRT_c, pval_c, likelihood_w_decoupled, likelihood_wo_decoupled,
   #                 LRT, pval  (index = shared gene names)
   ```
5. Persist results and compute summary:
   ```python
   adata.uns["lrt_decoupling"] = lrt_df.to_dict()
   n_decoupled = int((lrt_df["pval_c"] < lrt_pval_threshold).sum())
   n_coupled   = int((lrt_df["pval_c"] >= lrt_pval_threshold).sum())
   n_tested    = len(lrt_df)
   lrt_path    = None
   if output_dir:
       lrt_path = output_dir / "lrt_decoupling.parquet"
       lrt_df.to_parquet(lrt_path)
   ```
6. Return `LRTResult(n_genes_tested=n_tested, n_decoupled=n_decoupled,
   n_coupled=n_coupled, pct_decoupled=round(100*n_decoupled/n_tested, 2),
   lrt_table_path=lrt_path, metadata={"pval_threshold": lrt_pval_threshold})`

---

## 7. File Tree

```
backend/
├── types.py                                  ← Add VelocityResult, VelocityDownstreamResult, LRTResult
└── tools/
    ├── rna/
    │   └── velocity/
    │       ├── __init__.py
    │       └── scvelo.py                     ← rna_velocity_scvelo
    └── multi/
        └── velocity/
            ├── __init__.py
            ├── aggregate_peaks.py            ← multi_velocity_aggregate_peaks
            ├── knn_smooth.py                 ← multi_velocity_knn_smooth
            ├── recover_dynamics.py           ← multi_velocity_recover_dynamics
            ├── downstream.py                 ← multi_velocity_downstream
            └── lrt_decoupling.py             ← multi_velocity_lrt
```

---

## 8. Executor Auto-Wiring Extension

Add to [backend/executor.py](../backend/executor.py) in the auto-context extraction block:

```python
# Velocity key auto-wiring (analogous to embedding.obsm_key)
if "velocity" in adata.uns and isinstance(adata.uns["velocity"], dict):
    vk = adata.uns["velocity"].get("velocity_key")
    if vk:
        auto_context["velocity_key"] = vk
    ltk = adata.uns["velocity"].get("latent_time_key")
    if ltk:
        auto_context["latent_time_key"] = ltk
```

This lets `multi_velocity_downstream` receive `velocity_key` without the agent having to
specify it explicitly — just as `rna_cluster_leiden` receives `embedding_key` automatically.

---

## 9. Typical DAG Patterns

### 9.1 Full MultiVelo Pipeline (Multi-Omic Velocity)

```json
{
  "input_h5ad_path": "data/pbmc_rna_velocyto.h5ad",
  "layers": [
    {
      "tool": "multi_qc_intersect",
      "variants": [{"method": "intersect",
                    "params": {"atac_h5ad_path": "data/pbmc_atac.h5ad"}}]
    },
    {
      "tool": "rna_normalize_log1p",
      "variants": [{"method": "log1p", "params": {"target_sum": 10000}}]
    },
    {
      "tool": "rna_feature_selection_scanpy_hvg",
      "variants": [{"method": "scanpy_hvg", "params": {"n_top": 2000}}]
    },
    {
      "tool": "rna_embed_pca",
      "variants": [{"method": "pca", "params": {"n_pcs": 50}}]
    },
    {
      "tool": "atac_embed_lsi",
      "variants": [{"method": "lsi", "params": {"n_components": 50}}]
    },
    {
      "tool": "multi_embed_wnn",
      "variants": [{"method": "wnn", "params": {"n_neighbors": 30}}]
    },
    {
      "tool": "multi_velocity_aggregate_peaks",
      "variants": [{"method": "aggregate_peaks",
                    "params": {
                      "peaks_annot_path": "data/atac_peak_annotation.tsv",
                      "linkage_path": "data/feature_linkage.bedpe"
                    }}]
    },
    {
      "tool": "multi_velocity_knn_smooth",
      "variants": [{"method": "knn_smooth", "params": {}}]
    },
    {
      "tool": "multi_velocity_recover_dynamics",
      "variants": [
        {"method": "recover_dynamics",
         "params": {"max_iter": 5, "init_mode": "invert", "parallel": true}},
        {"method": "recover_dynamics",
         "params": {"max_iter": 5, "init_mode": "invert", "neural_net": true, "parallel": true}}
      ]
    },
    {
      "tool": "multi_velocity_downstream",
      "variants": [{"method": "downstream",
                    "params": {"compute_latent_time": true}}]
    }
  ],
  "objective_name": "velocity_likelihood",
  "evaluation": {"metrics": []}
}
```

### 9.2 RNA-Only Velocity (scVelo Baseline)

Note: normalization → HVG → PCA are all required predecessors. PCA provides `X_pca`
which gets auto-wired to `embedding_key` in `rna_velocity_scvelo`. The velocity tool
then calls `sc.pp.neighbors()` internally using that embedding.

```json
{
  "input_h5ad_path": "data/pbmc_rna_velocyto.h5ad",
  "layers": [
    {
      "tool": "rna_normalize_log1p",
      "variants": [{"method": "log1p", "params": {"target_sum": 10000}}]
    },
    {
      "tool": "rna_feature_selection_scanpy_hvg",
      "variants": [{"method": "scanpy_hvg", "params": {"n_top": 2000}}]
    },
    {
      "tool": "rna_embed_pca",
      "variants": [{"method": "pca", "params": {"n_pcs": 50}}]
    },
    {
      "tool": "rna_velocity_scvelo",
      "variants": [
        {"method": "scvelo", "params": {"mode": "dynamical"}},
        {"method": "scvelo", "params": {"mode": "stochastic"}}
      ]
    }
  ],
  "objective_name": "velocity_likelihood",
  "evaluation": {"metrics": []}
}
```

### 9.3 Epigenome Coupling Analysis (Standalone)

```json
{
  "layers": [
    "... (pipeline up through multi_velocity_recover_dynamics) ...",
    {
      "tool": "multi_velocity_lrt",
      "variants": [{"method": "lrt", "params": {}}]
    }
  ]
}
```

---

## 10. Implementation Order

| Phase | File | Tool ID | Depends on |
|-------|------|---------|-----------|
| 1 | `backend/types.py` | `VelocityResult`, `VelocityDownstreamResult`, `LRTResult` | — |
| 2 | `rna/velocity/scvelo.py` | `rna_velocity_scvelo` | Phase 1 |
| 3 | `multi/velocity/aggregate_peaks.py` | `multi_velocity_aggregate_peaks` | Existing `multi_qc_intersect` |
| 4 | `multi/velocity/knn_smooth.py` | `multi_velocity_knn_smooth` | Phase 3, existing `multi_embed_wnn` |
| 5 | `multi/velocity/recover_dynamics.py` | `multi_velocity_recover_dynamics` | Phase 1, 3, 4 |
| 6 | `multi/velocity/downstream.py` | `multi_velocity_downstream` | Phase 1, 5 |
| 7 | `multi/velocity/lrt_decoupling.py` | `multi_velocity_lrt` | Phase 1, 5 |
| 8 | `backend/executor.py` | velocity auto-wiring | Phase 5–6 |
| 9 | `__init__.py` files | Package discovery | All phases |

---

## 11. Key Design Decisions & Rationale

### Why scVelo as `rna_velocity_scvelo`?

Implementing it as `rna_velocity_scvelo` under `rna/velocity/` gives the agent a clean
baseline: run scVelo first to establish whether RNA dynamics are interpretable before adding
chromatin complexity. The agent can compare `mean_likelihood` between scVelo and MultiVelo
to quantify the gain from multi-omic data. scVelo also serves as a fallback when ATAC
is unavailable.

### Why keep `aggregate_peaks` and `knn_smooth` as separate tools?

- `aggregate_peaks` changes the feature space (peaks → genes) — expensive, rarely re-run
- `knn_smooth` depends on the WNN graph — re-run if neighbors change

Separating them enables independent caching and allows users who already have gene-level
ATAC data (e.g. ArchR gene scores) to skip `aggregate_peaks` and start from `knn_smooth`.

### Why not merge ATAC into RNA adata?

The existing system keeps them separate (`adata.uns["atac_h5ad_path"]` convention). MultiVelo
accepts two AnnData objects natively. Merging would bloat the primary h5ad and break the
auto-wiring conventions for ATAC tools. The path-based pattern is proven in WNN and SCENIC+.

### Why `fit_decoupling`, `weight_c`, `n_pcs`, `n_neighbors` are exposed in `recover_dynamics`

These are confirmed valid parameters of `mv.recover_dynamics_chrom()` (verified from source).
They control scientifically meaningful aspects: `fit_decoupling` enables Model 1 vs 2
discrimination, `weight_c` balances chromatin vs RNA in the 3D distance metric, and
`n_pcs`/`n_neighbors` control how MultiVelo selects representative cells for time assignment.
They are appropriately exposed to the agent for variant testing.

### Why `run_lrt` in `downstream.py` AND also a standalone tool?

`downstream.py` includes it as a convenience flag for simple pipelines. `lrt_decoupling.py`
as a standalone tool enables targeted re-analysis with different thresholds, or re-running
LRT without re-running the full downstream pipeline. This mirrors how eval tools can be
re-run independently.

---

## 12. Agent Prompt Additions

Add to the ToolConsultant system prompt (or tool registry docstrings) the following
heuristics so the agent knows when to invoke velocity tools:

```
Velocity Analysis Decision Tree:
- Has ATAC data + RNA + velocyto layers (Mu, Ms)?
  → Use MultiVelo pipeline: multi_velocity_aggregate_peaks → multi_velocity_knn_smooth
    → multi_velocity_recover_dynamics → multi_velocity_downstream
- Has RNA + velocyto layers (Mu, Ms), no ATAC?
  → Use RNA baseline: rna_velocity_scvelo
- User wants to compare RNA vs multi-omic velocity?
  → Run rna_velocity_scvelo first, then full MultiVelo pipeline; compare mean_likelihood
- User asks about epigenome-transcriptome coupling?
  → Run multi_velocity_lrt after multi_velocity_recover_dynamics
- User asks about cell fate / pseudotime?
  → Check if multi_velocity_downstream has been run; latent_time_key in adata.obs
- Velocyto layers missing?
  → Inform user: Mu/Ms layers must be generated externally via velocyto before any
    velocity tool. The agent cannot create these from existing h5ad alone.
```

---

## 13. Dependencies

```
scvelo >= 0.2.5         # rna_velocity_scvelo
multivelo >= 0.1.5      # all multi_velocity_* tools
loompy >= 3.0.7         # reading velocyto loom files (upstream, not in tools)
```

```bash
pip install multivelo scvelo
```
