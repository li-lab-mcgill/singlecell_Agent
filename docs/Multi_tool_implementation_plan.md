# Multimodal Tool Implementation Plan

## Current State

All 9 multimodal backend modules are 100% scaffolded with `NotImplementedError`. Each has: `KNOWN_METHODS`, `dispatch()` skeleton, method validation. The `r_scripts/multi/` directory exists but is **empty**. No multimodal method is implemented.

## Dispatch Pattern

`MultiBackend` holds `refs`, `runners`, and a reference to the parent `SingleCellBackend`:
```python
class MultiBackend:
    def __init__(self, *, refs, runners, parent_backend):
        self.refs = refs
        self.runners = runners
        self.parent = parent_backend
```

Key difference from RNA/ATAC: most tools take **dual inputs** (rna_adata + atac_adata) or reference atlases. Some return complex result types (`JointDEResult`, `GRN`).

## Result Types (from `backend/types.py`)

| Type | Used By | Fields |
|------|---------|--------|
| `JointDEResult` | joint_differential_expression | method, group_key, rna_table_path, atac_table_path, summary |
| `GRN` | grn_inference | method, n_tfs, n_targets, n_edges, edges_path, metadata |

Both have `.to_dict()`.

## Input Types

| Pattern | Tools | Signature |
|---------|-------|-----------|
| **Dual** (matched cells) | paired_integration, joint_de, joint_rna_velocity, grn_inference | `(rna_adata, atac_adata, ...)` |
| **Dual** (unmatched cells) | unpaired_integration | `(rna_adata, atac_adata, ...)` |
| **Multi** (3+ datasets) | mosaic_integration | `(adatas: List, modalities: List[str], ...)` |
| **Single** + reference | label_transfer | `(query_adata, *, reference_atlas, ...)` |
| **Single** | cross_modality_prediction, foundation_models | `(adata, ...)` |

## Implementation Contract

Do not implement integration methods until the modality data model is explicit. Multimodal correctness depends more on cell/feature alignment than on the wrapper call.

| Contract | Requirement |
|----------|-------------|
| Paired cells | For paired RNA+ATAC, require shared barcodes. Reindex both objects to the intersection and record dropped cells, or fail if overlap is below a threshold. |
| Representation | Prefer `MuData`/`muon` for paired multimodal outputs. If returning AnnData, explicitly encode modality in `obs["modality"]` and preserve source feature names. |
| RNA state | RNA input should have raw counts in `layers["counts"]` for generative models and log-normalized data for marker/label-transfer methods. |
| ATAC state | ATAC input should have peak count matrix plus valid peak coordinates; LSI is required for WNN-style methods unless computed internally. |
| Output files | If a tool writes `.h5mu`, return `output_h5mu_path` or ensure `output_h5ad_path` naming is not misleading. |
| Refs | Gene annotation, motif databases, genome FASTA, and pretrained models must be resolved through `refs` and recorded in `uns`. |
| Heavy methods | SCENIC+, CellOracle, Geneformer, scGPT, and scFoundation require explicit resource/model availability checks before import/training. |

---

## Phase 0: Data Model and Validation

Implement shared validators before method wrappers:

- `_validate_paired_modalities(rna_adata, atac_adata, min_overlap=0.8)`: checks barcode overlap, reorders cells, records alignment.
- `_validate_atac_peaks(atac_adata)`: checks peak coordinates in `var`.
- `_ensure_counts_layer(adata, modality)`: copies count-like `X` into `layers["counts"]` only if appropriate.
- `_to_mudata(rna_adata, atac_adata)`: creates a `MuData` object with `mod["rna"]` and `mod["atac"]`.
- `_write_multi_output(result, output_path)`: writes `.h5mu` for MuData and `.h5ad` for AnnData, returning the correct path key.

These validators should be unit-tested before any integration method is implemented.

---

## Phase 1: Paired Integration Tools

### 1.1 `_paired_integration.py` — RNA+ATAC same cells

| Method | Runtime | Package | Priority |
|--------|---------|---------|----------|
| `wnn` | R | Seurat v5 | **First** — best-defined for paired RNA+ATAC after LSI/PCA |
| `multivi` | Python | scvi-tools | Second — requires careful count setup and MuData/AnnData organization |
| `scglue` | Python | scglue | Third |
| `cobolt` | Python | cobolt | Fourth |

**Correctness requirements**
- Paired methods must not concatenate RNA cells and ATAC cells as separate observations.
- WNN requires RNA PCA and ATAC LSI or computes both internally in the R script.
- MultiVI requires count data and correct modality registration. Use `MuData` or the current scvi-tools recommended setup for paired RNA+ATAC; do not use naive `ad.concat([rna_adata, atac_adata])`.
- Store joint embeddings under a consistent key such as `mdata.obsm["X_wnn"]`/`mdata.obsm["X_multivi"]` or in both modality `obsm` slots with identical row order.

**MultiVI implementation outline:**
```python
def _run_multivi(rna_adata, atac_adata, *, batch_key=None, **_):
    import scvi
    import muon as mu

    rna_adata, atac_adata = _validate_paired_modalities(rna_adata, atac_adata)
    _ensure_counts_layer(rna_adata, "rna")
    _ensure_counts_layer(atac_adata, "atac")
    _validate_atac_peaks(atac_adata)
    mdata = mu.MuData({"rna": rna_adata, "atac": atac_adata})
    # Use the scvi-tools MultiVI setup appropriate for the installed version.
    # Register RNA counts and ATAC counts explicitly; do not concatenate cells.
    scvi.model.MULTIVI.setup_mudata(mdata, rna_layer="counts", atac_layer="counts", batch_key=batch_key)
    model = scvi.model.MULTIVI(mdata)
    model.train(max_epochs=100)
    mdata.obsm["X_multivi"] = model.get_latent_representation()
    mdata.uns["paired_integration"] = {"method": "multivi", "batch_key": batch_key}
    return mdata
```

**WNN (R) sketch:**
```python
def _run_wnn(rna_adata, atac_adata, *, runners, **_):
    if runners is None or getattr(runners, "r", None) is None:
        raise RuntimeError("WNN requires R runner (Seurat v5)")
    # Write both adatas to temp files
    tmp_rna = _write_temp_h5ad(rna_adata)
    tmp_atac = _write_temp_h5ad(atac_adata)
    tmp_out = _temp_h5ad_path()
    try:
        runners.r.run_script("multi/paired_integration_wnn.R",
            args={"rna_h5ad": tmp_rna, "atac_h5ad": tmp_atac, "output_h5ad": tmp_out})
        result = ad.read_h5ad(tmp_out)
        return result
    finally:
        for p in (tmp_rna, tmp_atac, tmp_out):
            Path(p).unlink(missing_ok=True)
```

### 1.2 `_unpaired_integration.py` — RNA+ATAC different cells

| Method | Runtime | Package | Priority |
|--------|---------|---------|----------|
| `scglue` | Python | scglue | **First** — uses gene regulatory graph |
| `liger` | R | rliger | Second |
| `seurat_cca` | R | Seurat | Third |

**scGLUE** needs `refs.get_gtf()` to build the guidance graph linking genes to peaks.

**Correctness requirements**
- scGLUE requires gene annotations on RNA genes and valid peak coordinates on ATAC peaks.
- Configure RNA with NB/ZINB and ATAC with Bernoulli/NB according to data representation; do not blindly use `"NB"` for both.
- Return modality-labeled combined AnnData or MuData with embeddings for each modality and `obs["modality"]`.
- Store the guidance graph metadata and reference annotation version.

```python
def _run_scglue(rna_adata, atac_adata, *, refs, **_):
    import scglue
    import anndata as ad
    # Build guidance graph from gene annotations
    gtf = refs.get_gtf("gencode_v44_human")
    scglue.data.get_gene_annotation(rna_adata, gtf=gtf)
    guidance = scglue.genomics.rna_atac_guidance(rna_adata, atac_adata)
    # Train model
    scglue.models.configure_dataset(rna_adata, "NB", use_highly_variable=True)
    scglue.models.configure_dataset(atac_adata, "Bernoulli", use_highly_variable=True)
    glue = scglue.models.fit_SCGLUE({"rna": rna_adata, "atac": atac_adata}, guidance)
    # Extract embeddings
    rna_adata.obsm["X_glue"] = glue.encode_data("rna", rna_adata)
    atac_adata.obsm["X_glue"] = glue.encode_data("atac", atac_adata)
    # Return combined
    rna_adata.obs["modality"] = "rna"
    atac_adata.obs["modality"] = "atac"
    combined = ad.concat([rna_adata, atac_adata], label="modality_source", keys=["rna", "atac"], join="outer")
    combined.uns["unpaired_integration"] = {"method": "scglue"}
    return combined
```

### 1.3 `_mosaic_integration.py` — heterogeneous modality combos

| Method | Runtime | Package | Priority |
|--------|---------|---------|----------|
| `multigrate` | Python | multigrate | **First** |
| `scmomat` | Python | scMoMaT | Second |
| `stabmap` | R | StabMap | Third |

---

## Phase 2: Label Transfer and Prediction

### 2.1 `_label_transfer.py` — annotate query from reference

| Method | Runtime | Package | Priority |
|--------|---------|---------|----------|
| `celltypist` | Python | celltypist | **First** — already used in RNA |
| `scanvi` | Python | scvi-tools | Second |
| `scarches` | Python | scarches | Third |
| `seurat_cca` | R | Seurat | Fourth |

All load reference via `refs.get_atlas(reference_atlas)`.

**Correctness requirements**
- `celltypist` is RNA-only unless the query has gene expression or gene activity features matching the model. For ATAC, require gene activity first or use RNA label transfer.
- Validate feature overlap between query and reference/model and record coverage.
- Store labels in `adata.obs["<method>_label"]` and confidence in `adata.obs["<method>_confidence"]`.

```python
def _run_celltypist(query_adata, *, reference_atlas, refs, modality="rna", **_):
    import celltypist
    # Load reference model
    atlas_path = refs.get_atlas(reference_atlas)
    model = celltypist.models.Model.load(atlas_path)
    predictions = celltypist.annotate(query_adata, model=model)
    query_adata.obs["celltypist_label"] = predictions.predicted_labels["predicted_labels"]
    query_adata.obs["celltypist_conf"] = predictions.probability_matrix.max(axis=1)
    query_adata.uns["label_transfer"] = {
        "method": "celltypist", "reference_atlas": reference_atlas, "modality": modality,
    }
    return query_adata
```

### 2.2 `_cross_modality_prediction.py` — predict RNA from ATAC or vice versa

| Method | Runtime | Package | Priority |
|--------|---------|---------|----------|
| `babel` | Python | BABEL | **First** |
| `scglue` | Python | scglue | Second |
| `polarbear` | Python | Polarbear | Third |

All are deep learning methods. Input is single-modality adata, output is predicted other modality.

---

## Phase 3: Joint Analysis

### 3.1 `_joint_differential_expression.py` — returns `JointDEResult`

| Method | Runtime | Package | Priority |
|--------|---------|---------|----------|
| `scanpy_joint` | Python | scanpy | **First** — run DE on both, align results |
| `limma_voom` | R | limma | Second |
| `mast_joint` | R | MAST | Third |

**Correctness requirements**
- `scanpy_joint` is exploratory. For condition-level inference, require `sample_key` and use pseudobulk/replicate-aware methods.
- Validate `group_key` exists in both modalities and has compatible categories.
- RNA and ATAC result tables should include modality-specific feature identifiers and coordinated group labels.

```python
def _run_scanpy_joint(rna_adata, atac_adata, *, group_key, **_) -> JointDEResult:
    import scanpy as sc
    # DE on RNA
    sc.tl.rank_genes_groups(rna_adata, groupby=group_key, method="wilcoxon")
    rna_table = _write_de_table(rna_adata.uns["rank_genes_groups"], "rna_de")
    # DA on ATAC
    sc.tl.rank_genes_groups(atac_adata, groupby=group_key, method="wilcoxon")
    atac_table = _write_de_table(atac_adata.uns["rank_genes_groups"], "atac_da")
    return JointDEResult(
        method="scanpy_joint", group_key=group_key,
        rna_table_path=rna_table, atac_table_path=atac_table,
        summary={"n_rna_groups": rna_adata.obs[group_key].nunique(),
                 "n_atac_groups": atac_adata.obs[group_key].nunique()},
    )
```

### 3.2 `_joint_rna_velocity.py` — chromatin-informed velocity

| Method | Runtime | Package | Priority |
|--------|---------|---------|----------|
| `multivelo` | Python | MultiVelo | **First** |
| `unitvelo_multi` | Python | UnitVelo | Second |

Both require `spliced`/`unspliced` layers in RNA adata and chromatin accessibility in ATAC adata.

Require paired cells, RNA velocity layers, ATAC peak coordinates, and the gene/peak linkage model expected by MultiVelo. Do not run on unpaired modalities.

### 3.3 `_grn_inference.py` — returns `GRN`

| Method | Runtime | Package | Priority |
|--------|---------|---------|----------|
| `scenic_plus` | Python | SCENIC+ (scenicplus) | **First** — most comprehensive |
| `celloracle` | Python | CellOracle | Second |
| `figr` | R | FIGR | Third |

All need `refs.get_motifs()`, `refs.get_gtf()`, `refs.get_genome()`.

SCENIC+ and CellOracle should be implemented only after ATAC motif enrichment, peak-to-gene linking, and reference handling are working. These are heavy multi-step workflows; expose a dry-run validation mode that checks refs, coordinates, and external binaries before training.

```python
def _run_scenic_plus(rna_adata, atac_adata, *, gene_annotation, refs, **_) -> GRN:
    import scenicplus
    # Build cisTopic object from ATAC
    # Run pycisTarget for motif enrichment
    # Run SCENIC+ GRN inference
    motifs = refs.get_motifs("jaspar2024_core_vertebrates")
    gtf = refs.get_gtf(gene_annotation)
    # ... complex multi-step pipeline ...
    return GRN(
        method="scenic_plus", n_tfs=n_tfs, n_targets=n_targets,
        n_edges=n_edges, edges_path=edges_path,
        metadata={"gene_annotation": gene_annotation},
    )
```

---

## Phase 4: Foundation Models

### 4.1 `_foundation_models.py` — pretrained model inference

| Model | Tasks | Package | Priority |
|-------|-------|---------|----------|
| `geneformer` | embed, predict_celltype | geneformer | **First** — Hugging Face hosted |
| `scgpt` | embed, predict_celltype, perturbation_response | scGPT | Second |
| `scfoundation` | embed | scFoundation | Third |

**Critical constraint**: "Heavy: cap to one loaded model per session (LRU=1)."

Foundation model implementation must validate gene identifier type, species, tokenizer vocabulary coverage, and model availability before loading weights. Store coverage stats and model version in `adata.uns["foundation_model"]`.

```python
def _run_geneformer(adata, *, task, refs, **_):
    model_path = refs.get_pretrained_model("geneformer")
    if task == "embed":
        # Tokenize genes, run through transformer, extract embeddings
        from geneformer import TranscriptomeTokenizer, EmbExtractor
        tokenizer = TranscriptomeTokenizer()
        tokens = tokenizer.tokenize_anndata(adata)
        extractor = EmbExtractor(model_path)
        embeddings = extractor.extract_embs(tokens)
        adata.obsm["X_geneformer"] = embeddings
    elif task == "predict_celltype":
        # Fine-tuned classification head
        ...
    adata.uns["foundation_model"] = {"model": "geneformer", "task": task}
    return adata
```

---

## R Scripts Needed (total: 7 new files)

| Script | Tool | R Package |
|--------|------|-----------|
| `multi/paired_integration_wnn.R` | Paired Integration | Seurat v5 |
| `multi/unpaired_integration_liger.R` | Unpaired Integration | rliger |
| `multi/unpaired_integration_seurat_cca.R` | Unpaired Integration | Seurat |
| `multi/label_transfer_seurat_cca.R` | Label Transfer | Seurat |
| `multi/mosaic_integration_stabmap.R` | Mosaic Integration | StabMap |
| `multi/joint_de_limma_voom.R` | Joint DE | limma |
| `multi/joint_de_mast.R` | Joint DE | MAST |

---

## Python Package Dependencies (new)

| Package | Tools | Install |
|---------|-------|---------|
| `scvi-tools` | MultiVI, scANVI, label transfer | `pip install scvi-tools` (likely already installed) |
| `muon` | Paired integration (MuData objects) | `pip install muon` |
| `scglue` | Unpaired integration, cross-modality prediction | `pip install scglue` |
| `multigrate` | Mosaic integration | `pip install multigrate` |
| `celltypist` | Label transfer | (likely already installed) |
| `scarches` | Label transfer | `pip install scarches` |
| `scenicplus` | GRN inference | `pip install scenicplus` |
| `celloracle` | GRN inference | `pip install celloracle` |
| `multivelo` | Joint RNA velocity | `pip install multivelo` |
| `geneformer` | Foundation models | `pip install geneformer` |
| `scgpt` | Foundation models | `pip install scgpt` |

---

## Reference Data Needs

| Resource | Used By | `refs` Method |
|----------|---------|---------------|
| Gene annotations (GTF) | scGLUE, GRN, cross-modality | `refs.get_gtf(name)` |
| Motif databases | GRN (SCENIC+, CellOracle) | `refs.get_motifs(db)` |
| Genome FASTA | GRN, motif scanning | `refs.get_genome(build)` |
| Reference atlases | Label transfer (all methods) | `refs.get_atlas(name)` |
| Pretrained models | Foundation models | `refs.get_pretrained_model(name)` |
| L-R databases | (indirect, via RNA CCC) | `refs.get_lr_db(name)` |

---

## Implementation Order

| Phase | Tools | Methods | Effort | Key Deps |
|-------|-------|---------|--------|----------|
| **Phase 0** | Data contracts | paired validators, peak validators, MuData writer, counts-layer helpers | required first | muon/anndata |
| **Phase 1** | Paired integration | wnn, multivi | 2 methods | Seurat/scvi-tools |
| **Phase 2** | Unpaired/mosaic integration | scglue, multigrate | 2 methods | scglue/multigrate |
| **Phase 3** | Label transfer + exploratory joint analysis | celltypist on RNA/gene activity, scanpy_joint | 2 methods | celltypist/scanpy |
| **Phase 4** | Replicate-aware and velocity methods | limma_voom, mast_joint, multivelo | 3 methods | R + multivelo |
| **Phase 5** | Heavy GRN/foundation models | scenic_plus, celloracle, geneformer, scgpt | 4 methods | refs + external models |
| **Phase 6** | Remaining methods | cobolt, scmomat, scarches, polarbear, unitvelo_multi, scfoundation, R integrations | remaining | various |

**Total**: 27 methods across 9 tools, 7 R scripts.

---

## Verification Checklist

For each implemented method:
- [ ] `dispatch()` routes correctly with both input adatas
- [ ] Dual-input methods correctly accept `(rna_adata, atac_adata)`
- [ ] Paired methods validate barcode overlap and reorder cells consistently
- [ ] Output format is explicit (`.h5mu` vs `.h5ad`) and return dict uses the matching path key
- [ ] ATAC inputs validate peak coordinates before coordinate-dependent methods
- [ ] Single-input methods correctly accept `(query_adata)` or `(adata)`
- [ ] Result stored in `adata.uns["<category>"]` or returned as typed result
- [ ] Joint embeddings stored in consistent key (e.g., `X_multivi`, `X_glue`, `X_wnn`)
- [ ] Typed results (`JointDEResult`, `GRN`): `.to_dict()` serializes cleanly
- [ ] R methods: dual h5ad temp round-trip, cleanup in `finally`
- [ ] Foundation models: LRU=1 memory constraint respected
- [ ] Reference atlas loading via `refs.get_atlas()` works
- [ ] Tool class in `tools.py` maps dual-input kwargs correctly (`rna_input_h5ad_path`, `atac_input_h5ad_path`)
- [ ] DAG executor can call the tool (note: dual-input tools need special handling in DAG)
