# ATAC Tool Implementation Plan

## Current State

All 12 ATAC backend modules are 100% scaffolded with `NotImplementedError`. Each has: `KNOWN_METHODS`, `dispatch()` skeleton, method validation, typed return signatures. The `r_scripts/atac/` directory exists but is **empty**. No ATAC method is implemented.

## Dispatch Pattern

Same as RNA. `AtacBackend` delegates to module `dispatch()`:
```python
# backend/atac/backend.py
def qc(self, adata, *, method, **kwargs):
    return _quality_control.dispatch(adata, method=method, refs=self.refs, runners=self.runners, **kwargs)
```

Key difference from RNA: ATAC tools operate on peak/fragment matrices (not gene expression). Standard embedding key is `X_lsi` (not `X_pca`). Many tools require genome build, gene annotations, and motif databases from `refs`.

## Implementation Contract

ATAC methods must declare whether they operate on an existing cell x peak matrix or require fragment-level files. Do not infer fragment-level QC from a peak matrix alone.

| Contract | Requirement |
|----------|-------------|
| Matrix shape | `adata.X` is cells x genomic features. Keep it sparse CSR/CSC where possible. |
| Peak coordinates | Accept either `adata.var_names` in `chr:start-end` format or columns `chrom`, `start`, `end`; validate before peak/gene/motif methods. |
| Fragment path | Fragment-dependent methods require `fragments_path` param or `adata.uns["fragments_path"]`. |
| Genome build | Methods using coordinates require `build` and matching references (`gtf`, blacklist, genome FASTA, motifs). |
| Output keys | LSI goes to `adata.obsm["X_lsi"]`; clusters go to `adata.obs["lsi_clusters"]` unless explicitly overridden. |
| Count state | ATAC matrices should remain count/binary accessibility matrices unless a method explicitly writes a transformed layer. |
| Pseudobulk | Condition-level DA must use replicate-aware pseudobulk when `sample_key`/donor information exists. |

## Result Types (from `backend/types.py`)

| Type | Used By | Fields |
|------|---------|--------|
| `PeakCallResult` | peak_calling | method, peaks_path, n_peaks, frip, metrics |
| `MotifResult` | motif_enrichment | method, motif_db, n_motifs, table_path, enrichment |
| `DEResult` | differential_accessibility | method, group_key, n_groups, n_genes, table_path, top_per_group, metrics |
| `LinkSet` | peak_to_gene_linking | method, n_links, links_path, metadata |

All have `.to_dict()` for serialization.

---

## Phase 1: Core Pipeline (Python-first)

Build the minimal ATAC analysis pipeline: QC → feature matrix → TF-IDF/LSI → clustering. All Python, no R dependency.

### 1.1 `_quality_control.py` — start with `basic`

| Method | Runtime | Package |
|--------|---------|---------|
| `basic` | Python | snapATAC2 / scanpy |
| `tss_enrichment` | Python | snapATAC2 / custom |
| `fragment_size` | Python | custom (pysam) |
| `frip` | Python | custom |

**`basic` implementation sketch:**
```python
def _run_basic(adata, *, min_counts=1000, max_counts=50000, min_features=500, min_cells=10, build="hg38", **_):
    import scanpy as sc
    sc.pp.filter_cells(adata, min_counts=min_counts)
    adata = adata[adata.obs["n_counts"] <= max_counts].copy()
    sc.pp.filter_cells(adata, min_genes=min_features)
    sc.pp.filter_genes(adata, min_cells=min_cells)
    adata.uns["qc"] = {
        "method": "basic",
        "build": build,
        "min_counts": min_counts,
        "max_counts": max_counts,
        "min_features": min_features,
        "min_cells": min_cells,
    }
    return adata
```

**Fragment-level methods**
- `tss_enrichment`: require `fragments_path`, `build`, and gene annotation/TSS reference. Store `adata.obs["tss_enrichment"]`.
- `fragment_size`: require `fragments_path`; store per-cell fragment size summaries in `adata.obs` and aggregate distribution in `adata.uns["fragment_size"]`.
- `frip`: require `fragments_path` and a peak set; store `adata.obs["frip"]`.
- Blacklist filtering requires `refs.get_blacklist(build)` and validated peak coordinates.

### 1.2 `_feature_matrix_construction.py` — start with `peaks`

| Method | Runtime | Package |
|--------|---------|---------|
| `peaks` | Python | snapATAC2 / custom |
| `tiles` | Python | snapATAC2 |
| `bins` | Python | snapATAC2 |

**Note**: If input adata already has a peak-by-cell matrix (common for 10x CellRanger output), this step may be a pass-through. The `tiles` and `bins` methods create fixed-width feature matrices from fragment files.

**Correctness requirements**
- Pass-through `peaks` must validate peak coordinates rather than only checking `adata.shape[1] > 0`.
- Building `peaks`, `tiles`, or `bins` from fragments requires `fragments_path` and barcodes aligned to `adata.obs_names`.
- Record feature coordinate schema in `adata.uns["feature_matrix"]`.

```python
def _run_peaks(adata, *, peakset=None, **_):
    # If adata.X already has peak matrix, validate and return
    if adata.X is not None and adata.shape[1] > 0 and _has_valid_peak_coordinates(adata):
        adata.uns["feature_matrix"] = {"method": "peaks", "n_features": adata.shape[1]}
        return adata
    # Otherwise build from fragments + peakset
    import snapatac2 as snap
    if peakset is None:
        raise ValueError("peaks method requires a peakset path")
    snap.pp.make_peak_matrix(adata, peak_file=peakset)
    adata.uns["feature_matrix"] = {"method": "peaks", "n_features": adata.shape[1]}
    return adata
```

### 1.3 `_tfidf_lsi.py` — start with `tfidf_lsi_v3`

| Method | Runtime | Package |
|--------|---------|---------|
| `tfidf_lsi_v3` | Python | custom (scipy + sklearn) |
| `tfidf_lsi_v1` | Python | custom |
| `snapatac2_svd` | Python | snapATAC2 |

TF-IDF + truncated SVD is the ATAC equivalent of PCA for RNA.

**Correctness requirements**
- Convert to CSR and handle zero-count cells before division.
- Optionally binarize counts (`binarize=True`) because many ATAC workflows use binary accessibility.
- Drop the first component by default but record both raw and retained component counts.
- Store depth correlation per component in `adata.uns["tfidf_lsi"]["depth_correlation"]`; this helps diagnose whether component 1 should be dropped.
- Validate `adata.obsm["X_lsi"]` exists and has expected shape after running.

```python
def _run_tfidf_lsi_v3(adata, *, n_components=50, drop_first=True, binarize=True, random_seed=0, **_):
    from scipy.sparse import issparse, diags
    from sklearn.decomposition import TruncatedSVD
    import numpy as np

    X = adata.X
    if not issparse(X):
        from scipy.sparse import csr_matrix
        X = csr_matrix(X)

    if binarize:
        X = X.copy()
        X.data[:] = 1
    row_sums = np.asarray(X.sum(axis=1)).ravel()
    if (row_sums == 0).any():
        raise ValueError("TF-IDF/LSI requires nonzero counts for every cell; run ATAC QC first.")

    # TF-IDF v3 (Signac default): log(TF * IDF)
    tf = X.copy()
    tf.data = tf.data / np.repeat(row_sums, np.diff(tf.indptr))
    idf = np.log1p(X.shape[0] / (1 + X.getnnz(axis=0)))
    tfidf = tf.multiply(idf)

    # LSI via truncated SVD
    n = n_components + (1 if drop_first else 0)
    svd = TruncatedSVD(n_components=n, random_state=random_seed)
    lsi = svd.fit_transform(tfidf)
    if drop_first:
        lsi = lsi[:, 1:]  # drop first component (correlated with sequencing depth)

    adata.obsm["X_lsi"] = lsi
    adata.uns["tfidf_lsi"] = {
        "method": "tfidf_lsi_v3", "n_components": n_components,
        "drop_first": drop_first,
        "binarize": binarize,
        "explained_variance_ratio": svd.explained_variance_ratio_.tolist(),
    }
    return adata
```

### 1.4 `_clustering.py` — `leiden` and `louvain`

| Method | Runtime | Package |
|--------|---------|---------|
| `leiden` | Python | scanpy + leidenalg |
| `louvain` | Python | scanpy + louvain |

**Comment in source**: "Identical to rna._clustering; may be worth factoring to shared helper."

```python
def _run_leiden(adata, *, embedding_key="X_lsi", resolution=1.0, n_neighbors=15, **_):
    import scanpy as sc
    if embedding_key not in adata.obsm:
        raise ValueError(f"embedding_key '{embedding_key}' not in adata.obsm. Run tfidf_lsi first.")
    sc.pp.neighbors(adata, use_rep=embedding_key, n_neighbors=n_neighbors)
    cluster_key = f"{embedding_key.replace('X_', '')}_clusters"
    sc.tl.leiden(adata, resolution=resolution, key_added=cluster_key)
    adata.uns["clustering"] = {
        "method": "leiden", "embedding_key": embedding_key,
        "resolution": resolution, "cluster_key": cluster_key,
        "n_clusters": int(adata.obs[cluster_key].nunique()),
    }
    return adata
```

---

## Phase 2: Analysis Tools (Python-first)

### 2.1 `_differential_accessibility.py` — start with `wilcoxon`

| Method | Runtime | Package | Priority |
|--------|---------|---------|----------|
| `wilcoxon` | Python | scanpy | **First** |
| `logreg` | Python | scanpy | Second |
| `edger_pseudobulk` | R | edgeR | Third |
| `deseq2_pseudobulk` | R | DESeq2 | Fourth |

**Correctness requirements**
- `wilcoxon`/`logreg` are exploratory peak marker methods, not publication-grade condition DA.
- Pseudobulk methods require `sample_key`, `group_key`, and optionally `condition_key`. Fail clearly if no replicate/donor column is available.
- Output tables should include peak coordinates, logFC/effect size, p-value, adjusted p-value, detection/accessibility fractions, and group labels.

```python
def _run_wilcoxon(adata, *, group_key, **_) -> DEResult:
    import scanpy as sc
    sc.tl.rank_genes_groups(adata, groupby=group_key, method="wilcoxon")
    # Extract results per group
    result = adata.uns["rank_genes_groups"]
    table_path = _write_da_table(result, group_key)
    top_per_group = _extract_top_per_group(result, top_n=20)
    return DEResult(
        method="wilcoxon", group_key=group_key,
        n_groups=int(adata.obs[group_key].nunique()),
        n_genes=adata.shape[1], table_path=table_path,
        top_per_group=top_per_group, metrics={},
    )
```

### 2.2 `_trajectory_inference.py` — start with `paga`

| Method | Runtime | Package |
|--------|---------|---------|
| `paga` | Python | scanpy |
| `slingshot` | R | slingshot |

Same as RNA PAGA but default `embedding_key="X_lsi"`.

Requires `group_key`; default only from `adata.uns["clustering"]["cluster_key"]` if available. Store metadata in `adata.uns["trajectory"]`.

### 2.3 `_batch_integration.py` — start with `harmony`

| Method | Runtime | Package |
|--------|---------|---------|
| `harmony` | Python | harmonypy |
| `scvi_atac` | Python | scvi-tools |
| `liger_atac` | R | rliger |

```python
def _run_harmony(adata, *, batch_key, **_):
    import harmonypy as hm
    if "X_lsi" not in adata.obsm:
        raise ValueError("Run tfidf_lsi before batch integration")
    ho = hm.run_harmony(adata.obsm["X_lsi"], adata.obs, batch_key)
    adata.obsm["X_harmony_lsi"] = ho.Z_corr.T
    adata.uns["batch_integration"] = {"method": "harmony", "batch_key": batch_key}
    return adata
```

---

## Phase 3: Specialized Tools

### 3.1 `_peak_calling.py` — returns `PeakCallResult`

| Method | Runtime | External Tool |
|--------|---------|---------------|
| `macs2` | CLI | `macs2 callpeak` |
| `macs3` | CLI | `macs3 callpeak` |
| `archr_iter` | R | ArchR |
| `snapatac2` | Python | snapATAC2 |

**MACS3 implementation sketch:**
```python
def _run_macs3(*, fragments_path, output_peaks_path, genome_size="hs", q_value=0.05, runners, build=None, **_):
    if runners is None or getattr(runners, "cli", None) is None:
        raise RuntimeError("macs3 requires CLI runner")
    import tempfile
    outdir = tempfile.mkdtemp()
    runners.cli.run([
        "macs3", "callpeak",
        "-t", str(fragments_path), "-f", "BEDPE",
        "-g", genome_size, "-q", str(q_value),
        "--outdir", outdir, "-n", "peaks",
        "--nomodel", "--keep-dup", "all",
    ])
    # Parse narrowPeak output
    peaks_file = Path(outdir) / "peaks_peaks.narrowPeak"
    if not peaks_file.exists():
        raise RuntimeError("MACS3 completed but did not produce peaks_peaks.narrowPeak")
    n_peaks = sum(1 for _ in open(peaks_file))
    shutil.copy(peaks_file, output_peaks_path)
    return PeakCallResult(method="macs3", peaks_path=Path(output_peaks_path), n_peaks=n_peaks)
```

### 3.2 `_gene_activity_score.py` — all R-dependent

| Method | Runtime | R Package |
|--------|---------|-----------|
| `cicero` | R | cicero |
| `archr` | R | ArchR |
| `signac` | R | Signac |

All require valid peak coordinates, `refs.get_gtf(gene_annotation)`, and R runner. Produce a cell x gene activity matrix as a separate AnnData object or `adata.obsm["gene_activity"]` with corresponding gene names in `adata.uns["gene_activity"]["genes"]`; do not store a matrix without gene labels.

### 3.3 `_motif_enrichment.py` — returns `MotifResult`

| Method | Runtime | Tool |
|--------|---------|------|
| `chromvar` | R | chromVAR |
| `homer` | CLI | HOMER `findMotifsGenome.pl` |

Both need `refs.get_motifs(motif_db)`. chromVAR produces per-cell TF deviation scores. HOMER produces per-group enrichment.

`chromvar` additionally requires genome FASTA and GC/background peak matching. Store deviations in `adata.obsm["X_chromvar"]` and motif names in `adata.uns["chromvar"]["motifs"]`.

### 3.4 `_peak_to_gene_linking.py` — returns `LinkSet`

| Method | Runtime | Tool |
|--------|---------|------|
| `cicero` | R | cicero |
| `peak2gene` | Python | correlation-based |
| `archr_p2g` | R | ArchR |

All need `refs.get_gtf(gene_annotation)`.

The first Python method should be `peak2gene`: require matched gene activity or RNA expression, validate distance window, compute correlations per cluster or globally, and write a links table with peak, gene, distance, correlation, p-value/FDR where available.

### 3.5 `_celltype_annotation.py`

| Method | Runtime | Approach |
|--------|---------|----------|
| `rna_label_transfer` | R | Signac/Seurat RNA→ATAC label transfer |
| `marker_peaks` | Python | Match peaks to known marker TF binding sites |

---

## R Scripts Needed (total: 12 new files)

| Script | Tool | R Package |
|--------|------|-----------|
| `atac/qc_tss_enrichment.R` | QC | GenomicRanges / ArchR |
| `atac/peak_calling_archr_iterative.R` | Peak Calling | ArchR |
| `atac/batch_integration_liger.R` | Batch Integration | rliger |
| `atac/gene_activity_cicero.R` | Gene Activity | cicero |
| `atac/gene_activity_archr.R` | Gene Activity | ArchR |
| `atac/gene_activity_signac.R` | Gene Activity | Signac |
| `atac/motif_enrichment_chromvar.R` | Motif Enrichment | chromVAR |
| `atac/differential_accessibility_edger.R` | DA | edgeR |
| `atac/differential_accessibility_deseq2.R` | DA | DESeq2 |
| `atac/peak_to_gene_cicero.R` | P2G Linking | cicero |
| `atac/peak_to_gene_archr.R` | P2G Linking | ArchR |
| `atac/trajectory_slingshot.R` | Trajectory | slingshot |

---

## Python Package Dependencies (new)

| Package | Tools | Install |
|---------|-------|---------|
| `snapatac2` | QC, feature matrix, TF-IDF, peak calling | `pip install snapatac2` |
| `pysam` | Fragment QC (fragment_size, FRiP) | `pip install pysam` |
| `pyranges` | Peak/gene interval operations | `pip install pyranges` |
| `pyfaidx` | Genome FASTA access | `pip install pyfaidx` |

---

## Reference Data Needs

| Resource | Used By | `refs` Method |
|----------|---------|---------------|
| Blacklist regions (hg38/mm10) | QC | `refs.get_blacklist(build)` |
| Gene annotations (GTF) | Gene activity, P2G, motif, annotation | `refs.get_gtf(name)` |
| Motif databases (JASPAR, CisBP) | Motif enrichment | `refs.get_motifs(db)` |
| Genome FASTA | Motif enrichment, HOMER | `refs.get_genome(build)` |
| Reference atlases | Annotation (label transfer) | `refs.get_atlas(name)` |

**Note**: `refs.get_blacklist()` is referenced in QC stub but may not exist in `ReferenceStore` yet — needs to be added.

---

## Implementation Order

| Phase | Tools | Methods | Effort | Deps |
|-------|-------|---------|--------|------|
| **Phase 1** | Core matrix pipeline | basic QC, peaks pass-through validation, tfidf_lsi_v3, leiden/louvain | 5 methods | scanpy/scipy/sklearn |
| **Phase 2** | Fragment-aware QC and peak calling | tss_enrichment, fragment_size, frip, macs3 | 4 methods | fragments + refs + CLI |
| **Phase 3** | Exploratory analysis | wilcoxon DA, logreg DA, paga trajectory, harmony integration | 4 methods | scanpy + harmonypy |
| **Phase 4** | Python specialized | peak2gene, marker_peaks, snapatac2_svd, scvi_atac | 4 methods | pyranges/scvi-tools |
| **Phase 5** | R/CLI specialized | gene activity, chromVAR, HOMER, slingshot, ArchR/Cicero methods | 17 methods | 12 R scripts |

**Total**: 32 methods across 12 tools, 12 R scripts.

---

## Verification Checklist

For each implemented method:
- [ ] `dispatch()` routes correctly
- [ ] Handler follows `_run_METHOD(adata, *, refs=None, runners=None, **_)` signature
- [ ] Result stored in `adata.uns["<category>"]` or returned as typed result
- [ ] Input contract distinguishes matrix-only vs fragment-level requirements
- [ ] Peak coordinate schema is validated before coordinate-dependent methods
- [ ] Fragment-dependent methods validate `fragments_path`
- [ ] Embedding stored in `adata.obsm["X_lsi"]` (not `X_pca`)
- [ ] Cluster key follows `f"{embedding_key.replace('X_', '')}_clusters"` convention
- [ ] Typed results (PeakCallResult, MotifResult, DEResult, LinkSet): `.to_dict()` works
- [ ] R methods: temp h5ad round-trip, cleanup in `finally`
- [ ] CLI methods: binary existence check, stderr capture
- [ ] Tool class in `tools.py` passes correct kwargs
- [ ] `agents/tools.py` adapter can call the backend method and validate expected outputs
