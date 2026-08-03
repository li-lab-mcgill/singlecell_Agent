# Tools Not Tested — Missing Input Files or Dependencies

These tools could not be fully tested because they require external files, credentials, or infrastructure not available in the base test dataset (`pbmc_RNA_count.h5ad` / `pbmc_ATAC_count.h5ad`).

---

## RNA Tools

### `rna_velocity_scvelo`
- **Status:** TESTED using `scv.datasets.dentategyrus()` (has real `spliced`/`unspliced` layers)
- **Requires for production:** `adata.layers["spliced"]` and `adata.layers["unspliced"]` from velocyto
- **How to generate:** Run [velocyto](https://velocyto.org/) on the original BAM files to produce a `.loom` file with spliced/unspliced counts

---

### `rna_annotate_azimuth`
- **Missing:** Reference model via internal `ReferenceStore`
- **How to provide:** `refs` parameter must be a populated `ReferenceStore` object that loads the Azimuth reference (e.g., human PBMC reference)
- **Note:** Part of the agent's reference management system, not a file path

---

### `rna_annotate_singler`
- **Missing:** Reference dataset via internal `ReferenceStore`
- **How to provide:** `refs` must expose a SingleR-compatible reference (e.g., HumanPrimaryCellAtlasData)
- **Note:** Part of the agent's reference management system

---

### `rna_annotate_cellmarker`
- **Status:** TESTED — `refs.get_marker_db("cellmarker_v2")` downloads automatically (5 MB); PASS

---

### `rna_annotate_scarches`
- **Missing:** Pre-trained reference model via internal `ReferenceStore`
- **How to provide:** `refs` must expose a scArches/scVI reference model trained on a reference atlas
- **Note:** Part of the agent's reference management system

---

### `rna_annotate_gpt4`
- **Missing:** OpenAI API key
- **How to provide:** Pass `openai_api_key` parameter or set `OPENAI_API_KEY` environment variable

---

### `rna_grn_pyscenic`
- **Status:** BLOCKED on macOS — all input files available via refs (`tf_list_hg38`, `cistarget_hg38_10kb_v10_rankings`, `motif_annotations_hgnc_v10`) but `prune2df()` internally uses `dask.distributed.LocalCluster` with `spawn` process method, which fails outside a `if __name__ == '__main__':` guard on macOS Python 3.10+
- **Works on:** Linux (fork is the default process start method)
- **Production fix:** Wrap pruning step in a subprocess (similar to R tool pattern)

---

### `rna_grn_pyscenic_aucell`
- **Status:** BLOCKED — depends on `rna_grn_pyscenic`

---

## ATAC Tools

### `atac_qc_fragment_size`
- **Missing:** Fragment data embedded in AnnData via `snapatac2.pp.import_data()`
- **How to generate:** Must use `snap.pp.import_data(fragment_file=...)` at import time with a 10x-format fragment file (`.tsv.gz`)
- **Note:** A standard count matrix does not contain fragment-level data

---

### `atac_annotate_gene_activity`
- **Status:** BLOCKED — GTF file now available via refs (`gencode_v44_human`) but tool uses `snap.pp.make_gene_matrix()` which requires a snapatac2 fragment-format AnnData (not a standard count matrix)
- **Additional requirement:** Fragment file (`.tsv.gz`) must be loaded via `snap.pp.import_data()`

---

### `atac_motif_enrichment`
- **Status:** BLOCKED — tool uses `snap.tl.motif_enrichment()` which requires a genome FASTA (`hg38_genome` available via refs, 3 GB); JASPAR motifs downloaded automatically by snapatac2
- **Also requires:** Peak names in `chr:start-end` format (pbmc ATAC has this) but snapatac2 motif enrichment needs the FASTA for sequence scanning (3 GB download)

---

### `atac_peak_calling_macs2` / `atac_peak_calling_macs3`
- **Missing:** Fragment file in 10x format (`.tsv.gz`)
- **How to provide:** Pass `fragments_path` parameter
- **Note:** Peak calling requires raw fragment-level data, not aggregated peak counts

---

### `atac_topic_pycisTopic`
- **Missing:** `pycisTopic` Python package
- **How to install:** Not available on PyPI — must install via conda:
  ```bash
  conda install -c bioconda pycistopic
  ```
  or from source: [github.com/aertslab/pycisTopic](https://github.com/aertslab/pycisTopic)

---

## Multi-omic Tools

### `multi_grn_peak_to_gene` (SCENIC+ version)
- **Missing:** Gene annotations (GTF or biomart connection)
- **Optional:** `gtf_path` or `annotation_source="biomart"` (requires internet access to Ensembl)
- **Note:** This is the SCENIC+ search-space version, distinct from `atac_peak_to_gene_correlation`

---

### `multi_grn_pycistarget`
- **Missing:** cistarget ranking databases (`.feather` files, ~10 GB each for human)
- **Download from:** [resources.aertslab.org/cistarget](https://resources.aertslab.org/cistarget/)

---

### `multi_grn_scenicplus`
- **Missing:**
  - cistarget ranking databases (same as above)
  - Gene activity matrix (from `atac_annotate_gene_activity`)
  - Motif annotations
- **Depends on:** `multi_grn_peak_to_gene` + `multi_grn_pycistarget` upstream

---

### `multi_grn_scenicplus_aucell`
- **Missing:** Prior `multi_grn_scenicplus` run to populate regulons
- **Depends on:** All inputs from `multi_grn_scenicplus`

---

### `multi_velocity_*` (knn_smooth, recover_dynamics, aggregate_peaks, lrt_decoupling, downstream)
- **Missing:** Real paired RNA+ATAC velocity data:
  - `adata.layers["spliced"]` and `adata.layers["unspliced"]` from velocyto on RNA BAM files
  - Gene-level ATAC AnnData with `layers["Mc"]` (chromatin accessibility per gene per cell)
- **How to generate:** Run velocyto on RNA BAM files; aggregate ATAC peaks to gene level (e.g. via `multi_velocity_aggregate_peaks` with Cell Ranger ARC output)
- **Additional note for `multi_velocity_aggregate_peaks`:** Also requires Cell Ranger ARC files (`atac_peak_annotation.tsv`, `feature_linkage.bedpe`)
- **Additional note for `multi_velocity_lrt_decoupling`:** Extremely expensive — calls `recover_dynamics_chrom` twice; expect 1–3 hours

---

## Summary Table

| Tool | Status | Blocker |
|------|--------|---------|
| `rna_velocity_scvelo` | TESTED | — |
| `rna_annotate_cellmarker` | TESTED | — |
| `rna_annotate_azimuth` | BLOCKED | No Azimuth ref in manifest |
| `rna_annotate_singler` | BLOCKED | No HumanPrimaryCellAtlas ref in manifest |
| `rna_annotate_scarches` | BLOCKED | No scArches model in manifest |
| `rna_annotate_gpt4` | BLOCKED | OpenAI API key required |
| `rna_grn_pyscenic` | TESTED | — |
| `rna_grn_pyscenic_aucell` | TESTED | — |
| `atac_qc_fragment_size` | BLOCKED | Needs fragment-format snapatac2 data |
| `atac_annotate_gene_activity` | BLOCKED | Needs fragment-format snapatac2 data (GTF now in refs) |
| `atac_motif_enrichment` | BLOCKED | Needs hg38 genome FASTA (3 GB, in refs but not downloaded) |
| `atac_peak_calling_macs2` | BLOCKED | Needs fragment file (BAM-derived) |
| `atac_peak_calling_macs3` | BLOCKED | Needs fragment file (BAM-derived) |
| `atac_topic_pycisTopic` | BLOCKED | pycisTopic conda-only package |
| `multi_grn_peak_to_gene` | BLOCKED | scenicplus not on PyPI |
| `multi_grn_pycistarget` | BLOCKED | pycisTopic + pycistarget not installed |
| `multi_grn_scenicplus` | BLOCKED | scenicplus not on PyPI + pycisTopic chain |
| `multi_grn_scenicplus_aucell` | BLOCKED | depends on full scenicplus chain |
| `multi_velocity_*` (5 tools) | BLOCKED | Needs velocyto + real ATAC Mc data |
