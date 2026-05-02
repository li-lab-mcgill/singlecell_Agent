# RNA Tool Implementation Plan

## Current State

9 implemented tools (core pipeline: qc, normalize, features, embed, batch integrate, cluster, annotate, DE, 2d projection). 6 fully-stubbed tools + 8 partial-stub methods within implemented tools. All stubs have: `KNOWN_METHODS`, `dispatch()` skeleton, method validation. All raise `NotImplementedError` with implementation hints.

## Implementation Contract

Every new method must define and enforce these pieces before running the algorithm:

| Contract | Requirement |
|----------|-------------|
| Input matrix state | State whether method expects raw counts, log-normalized expression, scaled data, or spliced/unspliced layers. Prefer `adata.layers["counts"]` for raw counts when present. |
| Required keys | Validate required `obs`, `var`, `layers`, `obsm`, and reference resources up front with clear `ValueError`/`RuntimeError` messages. |
| Output location | Store embeddings in `adata.obsm["X_<method>"]`, loadings in `adata.varm[...]`, annotations in `adata.obs[...]`, and method metadata in `adata.uns["<category>"]`. |
| Data preservation | Do not overwrite `adata.X` unless the method is explicitly a transformation step. Denoised/imputed outputs go into named layers. |
| Reproducibility | Expose `random_seed` for stochastic methods and record key params in `adata.uns`. |
| Size safety | Avoid unconditional `.toarray()` on large sparse matrices. Use sparse-aware code or fail with an actionable size error. |
| Tool adapter validation | `agents/tools.py` should validate expected output keys after backend execution, as existing PCA/clustering tools do. |

Preferred implementation order for RNA stubs is: `paga`, `nmf`, `scvelo`, `liana`, then QC R/CLI methods, then heavier or reference-model methods.

## Dispatch Pattern (for reference)

Every module follows:
```python
def dispatch(adata, *, method: str, refs=None, runners=None, **kwargs):
    if method not in KNOWN_METHODS:
        raise ValueError(...)
    if method == "x": return _run_x(adata, refs=refs, runners=runners, **kwargs)
    ...
```

Python methods modify adata in-place and return it. R methods use temp h5ad round-trip via `runners.r.run_script()`. Result types: modified `adata` (most), `DEResult` (DE), `CCCResult` (communication).

---

## Priority 1: Partial Stubs in Implemented Tools

These are single methods within already-working tools. Low risk, high value since the surrounding infrastructure is proven.

### 1.1 `_quality_control.py` — 4 stub methods

| Method | Runtime | Script/Package | Notes |
|--------|---------|----------------|-------|
| `scdblfinder` | R | `r_scripts/rna/doublet_scdblfinder.R` | Needs: write temp h5ad, run R script, read back with `adata.obs["scDblFinder_class"]` column |
| `soupx` | R | `r_scripts/rna/ambient_soupx.R` | Needs raw + filtered count matrices. May need `adata.layers["counts"]` pre-existing |
| `cellbender` | CLI | `runners.cli.run(["cellbender", "remove-background", ...])` | Subprocess, not R. Needs GPU detection fallback. Writes corrected h5ad directly |
| `emptydrops` | R | `r_scripts/rna/empty_drops.R` | DropletUtils::emptyDrops. Needs raw unfiltered matrix |

**Correctness requirements**
- `scdblfinder`: require raw UMI counts in `adata.layers["counts"]` or count-like `adata.X`; write `scDblFinder_score` and `scDblFinder_class`; filtering doublets should be controlled by `filter_doublets=True` rather than unconditional.
- `soupx`: require both raw droplet matrix and filtered matrix. Do not pretend a filtered h5ad alone is enough; accept explicit `raw_matrix_path`/`tod_path` or a documented `adata.uns["raw_matrix_path"]`.
- `cellbender`: this is a file-level CLI workflow, not an in-memory AnnData method. Require input raw h5/mtx path and output h5 path. Record CLI command, version if available, device used, and whether GPU fallback occurred.
- `emptydrops`: require raw unfiltered droplet matrix. Store FDR/statistics in `adata.obs`; filtering should be controlled by threshold params.

**Implementation pattern** (R methods):
```python
def _run_scdblfinder(adata, *, runners, **_):
    if runners is None or getattr(runners, "r", None) is None:
        raise RuntimeError("scDblFinder requires R runner")
    tmp_in = _write_temp_h5ad(adata)
    tmp_out = _temp_h5ad_path()
    try:
        runners.r.run_script("rna/doublet_scdblfinder.R",
            args={"input_h5ad": tmp_in, "output_h5ad": tmp_out})
        result = ad.read_h5ad(tmp_out)
        # Transfer doublet annotations back
        adata.obs["scDblFinder_class"] = result.obs["scDblFinder_class"]
        adata.obs["scDblFinder_score"] = result.obs["scDblFinder_score"]
        adata = adata[adata.obs["scDblFinder_class"] == "singlet"].copy()
        adata.uns["qc"] = {"method": "scdblfinder", ...}
        return adata
    finally:
        Path(tmp_in).unlink(missing_ok=True)
        Path(tmp_out).unlink(missing_ok=True)
```

**R scripts needed**: 4 new files in `r_scripts/rna/`

### 1.2 `_batch_integration.py` — 1 stub method

| Method | Runtime | Script/Package |
|--------|---------|----------------|
| `liger` | R | `r_scripts/rna/batch_integration_liger.R` |

Follow existing `_run_harmony()` pattern. LIGER produces a joint embedding → store in `adata.obsm["X_liger"]`.

**R script needed**: `r_scripts/rna/batch_integration_liger.R`

### 1.3 `_celltype_annotation.py` — 3 stub methods

| Method | Runtime | Script/Package | Notes |
|--------|---------|----------------|-------|
| `singler` | R | `r_scripts/rna/celltype_annotation_singler.R` | Uses Bioconductor SingleR. Needs reference dataset from `refs` |
| `azimuth` | R | `r_scripts/rna/celltype_annotation_azimuth.R` | Seurat ecosystem. Needs pre-built Azimuth reference |
| `scarches` | Python | scArches package | Needs pretrained model from `refs.get_pretrained_model()` |

**R scripts needed**: 2 new files. scArches is Python-only.

---

## Priority 2: Full-Stub Tools — Python-first methods

Implement the easiest Python method per tool first. Each tool already has dispatch + KNOWN_METHODS.

### 2.1 `_imputation.py` — 4 methods

| Method | Runtime | Package | Priority |
|--------|---------|---------|----------|
| `magic` | Python | `magic-impute` | **First** — well-maintained, simple API |
| `dca` | Python | `dca` (TF-based) | Second |
| `alra` | R | `SeuratWrappers::RunALRA` | Third |
| `saver` | R | `SAVER` | Fourth |

**Correctness requirements**
- Imputation is not a default preprocessing step. Treat it as denoising/visualization unless the user explicitly requests downstream use.
- Store outputs in layers such as `adata.layers["magic_imputed"]`; never silently replace `adata.X`.
- Record source matrix, params, and warning in `adata.uns["imputation"]`.
- Reject DE/DA-style use unless a caller explicitly selects an imputed layer.

**MAGIC implementation sketch:**
```python
def _run_magic(adata, **_):
    import magic
    magic_op = magic.MAGIC()
    adata_magic = magic_op.fit_transform(adata)
    adata.layers["magic_imputed"] = adata_magic.X
    adata.uns["imputation"] = {"method": "magic"}
    return adata
```

### 2.2 `_gene_program_inference.py` — 4 methods

| Method | Runtime | Package | Priority |
|--------|---------|---------|----------|
| `nmf` | Python | `sklearn.decomposition.NMF` | **First** — no external deps |
| `hotspot` | Python | `hotspot` | Second |
| `scenic` | Python/R | `pyscenic` or `SCENIC` | Third — complex multi-step |
| `pagoda2` | R | `pagoda2` | Fourth |

**Correctness requirements**
- NMF requires nonnegative input. Use normalized/log expression or counts after appropriate scaling, and fail if negative values are detected.
- Avoid dense conversion for large matrices. If using sklearn NMF, cap matrix size or accept `max_cells`/`max_genes` and document subsampling.
- Store cell program scores in `adata.obsm["X_nmf"]`, gene loadings in `adata.varm["nmf_loadings"]`, and top genes per program in `adata.uns["gene_programs"]["programs"]`.
- SCENIC is a multi-step GRN workflow, not just a gene program method. Keep it later unless motif databases and TF lists are available through `refs`.

**NMF implementation sketch:**
```python
def _run_nmf(adata, *, n_programs=20, **_):
    from sklearn.decomposition import NMF
    model = NMF(n_components=n_programs, random_state=0)
    W = model.fit_transform(adata.X.toarray() if issparse(adata.X) else adata.X)
    H = model.components_
    adata.obsm["X_nmf"] = W
    adata.varm["nmf_loadings"] = H.T
    adata.uns["gene_programs"] = {"method": "nmf", "n_programs": n_programs}
    return adata
```

### 2.3 `_trajectory_inference.py` — 4 methods

| Method | Runtime | Package | Priority |
|--------|---------|---------|----------|
| `paga` | Python | `scanpy` (built-in) | **First** — no extra deps |
| `palantir` | Python | `palantir` | Second |
| `slingshot` | R | `slingshot` | Third |
| `monocle3` | R | `monocle3` | Fourth |

**Correctness requirements**
- PAGA requires a grouping column. Accept `group_key`; default only if a clear cluster key exists in `adata.uns["clustering"]["cluster_key"]`.
- Validate `embedding_key in adata.obsm` before recomputing neighbors.
- Store graph in `adata.uns["paga"]`, optional layout in `adata.obsm["X_paga"]` or `adata.uns["paga"]["pos"]`, and metadata in `adata.uns["trajectory"]`.
- Palantir/Monocle/Slingshot require root/start cells or root group for meaningful pseudotime. Do not invent roots silently.

**PAGA implementation sketch:**
```python
def _run_paga(adata, *, embedding_key="X_pca", group_key=None, **_):
    import scanpy as sc
    if embedding_key not in adata.obsm:
        raise ValueError(f"{embedding_key!r} not found in adata.obsm")
    if group_key is None:
        group_key = adata.uns.get("clustering", {}).get("cluster_key")
    if not group_key or group_key not in adata.obs:
        raise ValueError("PAGA requires group_key or adata.uns['clustering']['cluster_key']")
    sc.pp.neighbors(adata, use_rep=embedding_key)
    sc.tl.paga(adata, groups=group_key)
    adata.uns["trajectory"] = {"method": "paga", "embedding_key": embedding_key, "group_key": group_key}
    return adata
```

### 2.4 `_rna_velocity.py` — 3 methods

| Method | Runtime | Package | Priority |
|--------|---------|---------|----------|
| `scvelo` | Python | `scvelo` | **First** — standard tool |
| `unitvelo` | Python | `unitvelo` | Second |
| `velocyto` | CLI+Python | `velocyto` | Third — needs BAM preprocessing |

**Requires**: `spliced` and `unspliced` layers in adata.

**Correctness requirements**
- Validate `spliced_key` and `unspliced_key` exist in `adata.layers`; do not overwrite existing standard layers unless keys differ.
- Add params for `mode` (`stochastic` first; `dynamical` later), `n_neighbors`, `n_pcs`, and `basis`.
- Run `scv.pp.filter_and_normalize`, `scv.pp.moments`, then velocity/graph. Record preprocessing params.
- Store `adata.layers["velocity"]`, `adata.uns["velocity_graph"]`, and metadata in `adata.uns["rna_velocity"]`.

**scVelo implementation sketch:**
```python
def _run_scvelo(adata, *, spliced_key="spliced", unspliced_key="unspliced", mode="stochastic", n_pcs=30, n_neighbors=30, **_):
    import scvelo as scv
    for key in (spliced_key, unspliced_key):
        if key not in adata.layers:
            raise ValueError(f"RNA velocity requires adata.layers[{key!r}]")
    if spliced_key != "spliced":
        adata.layers["spliced"] = adata.layers[spliced_key]
    if unspliced_key != "unspliced":
        adata.layers["unspliced"] = adata.layers[unspliced_key]
    scv.pp.filter_and_normalize(adata)
    scv.pp.moments(adata, n_pcs=n_pcs, n_neighbors=n_neighbors)
    scv.tl.velocity(adata, mode=mode)
    scv.tl.velocity_graph(adata)
    adata.uns["rna_velocity"] = {"method": "scvelo", "mode": mode, "spliced_key": spliced_key, "unspliced_key": unspliced_key}
    return adata
```

### 2.5 `_perturbation_analysis.py` — 3 methods

| Method | Runtime | Package | Priority |
|--------|---------|---------|----------|
| `mixscape` | Python | `pertpy` / custom | **First** |
| `gears` | Python | `gears` | Second — deep learning |
| `cpa` | Python | `cpa` (scvi-tools) | Third |

**All require `perturbation_key`** — column in `adata.obs` identifying perturbation condition.

**Correctness requirements**
- Also require a control condition key/value (`control_label`) for Mixscape/CPA style analyses.
- Validate guide/perturbation labels are not one cell per category; enforce `min_cells_per_condition`.
- Record condition counts in `adata.uns["perturbation_analysis"]`.

### 2.6 `_cell_cell_communication.py` — 3 methods (returns `CCCResult`)

| Method | Runtime | Package | Priority |
|--------|---------|---------|----------|
| `liana` | Python | `liana-py` | **First** — wraps multiple methods |
| `cellphonedb` | Python | `cellphonedb` | Second |
| `cellchat` | R | `CellChat` | Third |

**Requires**: `group_key` (cell type column), `species`, `refs.get_lr_db()` (ligand-receptor database).

**Correctness requirements**
- Require normalized/log expression and a biologically meaningful `group_key` such as cell type or cluster annotation.
- Enforce `min_cells_per_group` and `min_expr_prop` to reduce spurious interactions.
- Resolve species/resource explicitly; do not hardcode human resource for mouse data.
- Return `CCCResult` with table path, number of interactions, resource name, group counts, and filtering params.

**LIANA implementation sketch:**
```python
def _run_liana(adata, *, group_key, species, refs=None, resource_name="consensus", min_cells_per_group=10, **_):
    import liana as li
    if group_key not in adata.obs:
        raise ValueError(f"group_key {group_key!r} not found in adata.obs")
    counts = adata.obs[group_key].value_counts()
    if (counts < min_cells_per_group).any():
        raise ValueError("LIANA requires at least min_cells_per_group cells in every group")
    li.mt.rank_aggregate(adata, groupby=group_key, resource_name=resource_name)
    # Extract results
    result_df = adata.uns["liana_res"]
    table_path = _write_result_table(result_df)
    return CCCResult(
        method="liana", n_pairs=len(result_df),
        table_path=table_path, summary={"species": species, "group_key": group_key, "resource_name": resource_name}
    )
```

---

## R Scripts Needed (total: 11 new files)

| Script | Tool | R Package |
|--------|------|-----------|
| `rna/doublet_scdblfinder.R` | QC | scDblFinder (Bioconductor) |
| `rna/ambient_soupx.R` | QC | SoupX |
| `rna/empty_drops.R` | QC | DropletUtils (Bioconductor) |
| `rna/batch_integration_liger.R` | Batch Integration | rliger |
| `rna/celltype_annotation_singler.R` | Annotation | SingleR (Bioconductor) |
| `rna/celltype_annotation_azimuth.R` | Annotation | Azimuth (Seurat) |
| `rna/imputation_alra.R` | Imputation | SeuratWrappers::RunALRA |
| `rna/imputation_saver.R` | Imputation | SAVER |
| `rna/gene_programs_pagoda2.R` | Gene Programs | pagoda2 |
| `rna/trajectory_slingshot.R` | Trajectory | slingshot |
| `rna/trajectory_monocle3.R` | Trajectory | monocle3 |

All follow the existing R script protocol: `--args-json` input, JSON stdout output, temp h5ad round-trip.

---

## Python Package Dependencies (new)

| Package | Tools | Install |
|---------|-------|---------|
| `magic-impute` | Imputation (MAGIC) | `pip install magic-impute` |
| `scvelo` | RNA Velocity | `pip install scvelo` |
| `liana-py` | Cell-Cell Communication | `pip install liana` |
| `pertpy` | Perturbation (Mixscape) | `pip install pertpy` |
| `gears` | Perturbation (GEARS) | `pip install gears` |
| `hotspot` | Gene Programs | `pip install hotspot` |
| `pyscenic` | Gene Programs (SCENIC) | `pip install pyscenic` |
| `palantir` | Trajectory | `pip install palantir` |
| `scarches` | Annotation | `pip install scarches` |
| `dca` | Imputation (DCA) | `pip install dca` |

---

## Implementation Order

| Phase | Tools | Methods | Effort |
|-------|-------|---------|--------|
| **Phase 1** | Partial stubs (QC, batch, annotation) | scdblfinder, soupx, cellbender, emptydrops, liger, singler, azimuth, scarches | 8 methods, 6 R scripts |
| **Phase 2** | Python-first full stubs with clear contracts | paga, nmf, scvelo, liana | 4 methods, 0 R scripts |
| **Phase 3** | QC and reference methods after contracts | scdblfinder, soupx, emptydrops, singler, azimuth, scarches | 6 methods, 5 R scripts |
| **Phase 4** | Denoising/perturbation/secondary methods | magic, mixscape, dca, hotspot, palantir, unitvelo, cellphonedb, gears | 8 methods |
| **Phase 5** | Heavy R/deep methods | alra, saver, pagoda2, scenic, slingshot, monocle3, cellchat, cpa, cellbender, liger | 10 methods |

**Total**: 28 methods, 11 R scripts.

---

## Verification Checklist

For each implemented method:
- [ ] `dispatch()` routes to the new handler correctly
- [ ] Handler follows the `_run_METHOD(adata, *, runners=None, refs=None, **_)` signature
- [ ] Result stored in `adata.uns["<category>"]` with method + params
- [ ] Required input keys/layers/resources are validated before running
- [ ] Expected output keys are validated after running
- [ ] Method does not overwrite `adata.X` unless it is explicitly a transform
- [ ] R methods: temp h5ad round-trip works, cleanup in `finally` block
- [ ] Typed results (CCCResult): `.to_dict()` serializes cleanly
- [ ] Method registered in `KNOWN_METHODS`
- [ ] Tool class in `tools.py` passes correct kwargs to backend
- [ ] `agents/tools.py` adapter can call the backend method and validate expected outputs
