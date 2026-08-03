# GLUE Implementation Plan

## Overview

GLUE (**G**raph-**L**inked **U**nified **E**mbedding; Chen et al. 2022, *Nature Biotechnology*)
integrates **unpaired** multi-omics data (e.g., scRNA-seq + scATAC-seq that were not measured in
the same cells) by building a regulatory guidance graph that links genes to chromatin peaks via
genomic proximity. A variational autoencoder is then trained across both modalities with the
graph as a structural prior, producing:

- **Joint cell embeddings** (`obsm["X_glue"]`) for both RNA and ATAC cells, enabling UMAP and
  clustering across modalities
- **Feature embeddings** (`varm["X_glue"]`) for every gene and peak, enabling cosine-similarity-
  based peak-to-gene linkage and TF-gene network inference entirely from the learned latent space

GLUE's key niche is **unpaired integration** — the only existing multi-modal tools (WNN, MOFA,
MultiVI) require cells measured in both modalities simultaneously. GLUE does not.

---

## Gap Analysis: New vs. Existing

### What GLUE reuses without modification

| Existing Tool ID | Role in GLUE pipeline |
|---|---|
| `rna_qc_basic` | Cell/gene QC before GLUE |
| `rna_normalize_log1p` | Standard RNA normalization |
| `rna_feature_seurat_v3` | HVG selection (2000 genes, Seurat v3) |
| `rna_embed_pca` | PCA encoder input for GLUE (`n_comps=100`) |
| `atac_qc_basic` | ATAC QC |
| `atac_embed_lsi` | LSI encoder input for GLUE (`n_components=100`) |
| `multi_qc_intersect` | Cell barcode alignment for shared cells (if any) |
| `multi_cluster_leiden` | Leiden clustering on `X_glue` embedding |
| `multi_cluster_louvain` | Louvain clustering on `X_glue` embedding |
| `rna_embed_umap` | UMAP on `X_glue` embedding |
| `eval_silhouette` | Silhouette on `X_glue` + cluster assignments |
| `eval_ilisi_clisi` | Batch mixing on `X_glue` |
| `eval_kbet` | kBET on `X_glue` |

### What is new (4 tools)

| Tool ID | Stage | What it does |
|---|---|---|
| `multi_preprocess_glue_graph` | `multi/preprocess/` | Builds regulatory guidance graph (RNA genes ↔ ATAC peaks via genomic proximity) |
| `multi_embed_glue` | `multi/embed/` | Trains GLUE model; extracts cell embeddings `X_glue` and feature embeddings |
| `multi_peak2gene_glue` | `multi/grn/` | Peak-to-gene links via cosine similarity in GLUE feature space |
| `multi_grn_glue` | `multi/grn/` | TF-gene regulatory network bridged by GLUE feature embeddings |

### Why NOT to fold into existing tools

`multi_preprocess_glue_graph` cannot reuse any existing preprocessing tool because none builds a
`networkx.MultiDiGraph` linking gene vars to peak vars through genomic overlap.

`multi_peak2gene_glue` is distinct from `atac_peak2gene_correlation` (Pearson correlation on
expression/accessibility matrices), `atac_peak2gene_cicero` (co-accessibility), and
`multi_grn_peak_to_gene` (random forest importance + Spearman): it operates purely on cosine
similarity of learned feature embedding vectors — no expression or accessibility matrix is
consumed after training.

`multi_grn_glue` is distinct from `multi_grn_scenicplus` (which requires pycisTopic LDA topics,
pycistarget cisTarget enrichment, and a full SCENIC+ object) and `rna_grn_grnboost2` (RNA-only
co-expression). GLUE GRN bridges TF binding motifs through peak feature embeddings to gene
targets, requiring the GLUE feature latent space as the regulatory bridge.

---

## New Tool Specifications

### 1. `multi_preprocess_glue_graph`

**File:** `backend/tools/multi/preprocess/glue_graph.py`

**Purpose:** Annotate RNA `var` and ATAC `var` with genomic coordinates, then construct the
regulatory guidance graph that GLUE will use as a structural prior. This step must run after HVG
selection and LSI computation so that HVG markers are propagated to reachable ATAC peaks.

**Inputs (via `run()` signature):**
```python
def run(
    adata,                              # RNA AnnData: needs rna.var w/ gene names, HVG markers
    *,
    atac_h5ad_path: str | Path | None = None,   # from adata.uns["atac_h5ad_path"] if None
    genome_assembly: str = "hg38",      # "hg38" or "mm10"; determines GTF from refs store
    gtf_path: str | Path | None = None, # explicit GTF override (skips refs store lookup)
    use_highly_variable: bool = True,   # propagate HVG status to reachable ATAC peaks
    gene_region: str = "combined",      # "combined" (promoter + body), "promoter" (upstream window only), or "gene_body"
    promoter_len: int = 2000,           # upstream window in bp for promoter definition
    output_dir: Path | None = None,     # where to save guidance.graphml.gz
) -> object:
```

**Algorithm:**
1. Load ATAC AnnData from `adata.uns["atac_h5ad_path"]` or `atac_h5ad_path`
2. Annotate RNA `var` with genomic coordinates. `gtf_by` must be specified — GENCODE GTFs have
   both `gene_name` (symbols like `"TP53"`) and `gene_id` (Ensembl IDs like `"ENSG..."`);
   without this argument the join silently produces all-NaN coordinate columns:
   ```python
   scglue.data.get_gene_annotation(
       rna,
       gtf=gtf_path,
       gtf_by="gene_name",  # use "gene_id" if rna.var_names are Ensembl IDs
   )
   if rna.var["chrom"].isna().all():
       raise ValueError(
           "Gene annotation produced no coordinate matches. "
           "Check that gtf_by='gene_name' matches your rna.var_names format. "
           "Use gtf_by='gene_id' for Ensembl ID var_names."
       )
   ```
   GTF sourced from refs store: `refs.get_gtf("gencode_v44_hg38")` (human) or
   `refs.get_gtf("gencode_vM33_mm10")` (mouse). Adds `chrom`, `chromStart`, `chromEnd`
   (and `strand` when present in GTF) to `rna.var`.
3. Annotate ATAC `var` by manually parsing peak names from `atac.var_names` (format must be
   `chr:start-end`; `scglue.data.get_peak_annotation()` does **not** exist):
   ```python
   assert all(":" in v and "-" in v for v in atac.var_names[:5]), (
       "ATAC var_names must be 'chr:start-end' format"
   )
   split = atac.var_names.str.split(r"[:-]")
   atac.var["chrom"]      = split.map(lambda x: x[0])
   atac.var["chromStart"] = split.map(lambda x: x[1]).astype(int)
   atac.var["chromEnd"]   = split.map(lambda x: x[2]).astype(int)
   ```
4. Build guidance graph (returns `networkx.MultiDiGraph`; subclass of `Graph`, accepted by
   `fit_SCGLUE` and `check_graph`):
   ```python
   guidance = scglue.genomics.rna_anchored_guidance_graph(
       rna, atac,
       propagate_highly_variable=use_highly_variable,  # built-in; replaces manual Step 6
       gene_region=gene_region,
       promoter_len=promoter_len,
       extend_range=0,
   )
   ```
   Nodes = all RNA genes + ATAC peaks; each edge carries `weight` ∈ (0,1] and `sign` ∈
   {-1, +1}; self-loops have weight=1, sign=1. HVG propagation to reachable peaks is handled
   internally by `propagate_highly_variable=True` — no separate step required.
5. Validate: `scglue.graph.check_graph(guidance, [rna, atac])` — verifies full feature coverage,
   edge attributes, and self-loops before anything is saved
6. Always write the graph to disk — `networkx.MultiDiGraph` cannot be round-tripped through
   h5ad (h5py cannot serialize graph objects), so there is no in-memory handoff mechanism.
   When `output_dir=None`, fall back to a temporary directory so downstream tools always
   receive a valid file path via `adata.uns["glue_graph_path"]`:
   ```python
   import tempfile
   graph_dir  = output_dir if output_dir else Path(tempfile.mkdtemp())
   graph_path = graph_dir / "guidance.graphml.gz"
   nx.write_graphml(guidance, str(graph_path))
   adata.uns["glue_graph_path"] = str(graph_path)
   ```

**Outputs:**
- `adata.uns["glue_graph_path"]` = path to saved GraphML (always set; written to temp dir when `output_dir=None`)
- `adata.var`: updated with `chrom`, `chromStart`, `chromEnd`
- ATAC AnnData on disk updated with peak coordinate columns + propagated HVG flags
- Returns RNA AnnData

**Key dependencies:** `scglue`, `networkx`; GTF from existing refs store

**Relation to refs store:** Uses `refs.get_gtf("gencode_v44_hg38")` (human) or
`refs.get_gtf("gencode_vM33_mm10")` (mouse). Both already exist in `backend/refs/manifest.py`.
No new refs entries needed.

---

### 2. `multi_embed_glue`

**File:** `backend/tools/multi/embed/glue.py`

**Purpose:** Train the GLUE model on preprocessed RNA and ATAC data guided by the regulatory
graph. Extract per-cell latent embeddings (`X_glue`) and per-feature latent embeddings
(`varm["X_glue"]`) for both modalities.

**Inputs (via `run()` signature):**
```python
def run(
    adata,                              # RNA AnnData: needs X_pca, layers["counts"], HVG flags
    *,
    atac_h5ad_path: str | Path | None = None,   # from adata.uns["atac_h5ad_path"] if None
    glue_graph_path: str | Path | None = None,  # from adata.uns["glue_graph_path"] if None
    n_latent: int = 50,                 # maps to SCGLUEModel(latent_dim=n_latent)
    n_epochs: int = 500,                # maps to fit_kws={"max_epochs": n_epochs}
    use_highly_variable: bool = True,   # restrict training to HVG features
    batch_key: str | None = None,       # obs column for batch correction (optional)
    use_gpu: bool = True,               # if False, sets CUDA_VISIBLE_DEVICES="" before training
    random_seed: int = 0,               # maps to init_kws={"random_seed": random_seed}
    embedding_key: str = "X_glue",
    output_dir: Path | None = None,
) -> object:
```

**Algorithm:**
1. Resolve ATAC h5ad path (from param or `adata.uns["atac_h5ad_path"]`)
2. Resolve graph path (from param or `adata.uns["glue_graph_path"]`)
3. Load ATAC AnnData and guidance graph (`networkx.MultiDiGraph`)
4. Assert prerequisite layer exists; configure datasets — `batch_key` maps to `use_batch`:
   ```python
   assert "counts" in adata.layers, (
       "RNA adata must have layers['counts'] (raw integer counts). "
       "Ensure rna_normalize_log1p ran before multi_embed_glue (it backs up raw counts). "
       "configure_dataset raises ValueError if this layer is absent."
   )
   scglue.models.configure_dataset(
       rna, prob_model="NB", use_highly_variable=True,
       use_layer="counts", use_rep="X_pca",
       use_batch=batch_key,
   )
   scglue.models.configure_dataset(
       atac, prob_model="NB", use_highly_variable=True,
       use_rep="X_lsi",
       use_batch=batch_key,
   )
   ```
5. Subset graph to HVG features only — `.copy()` required because `.subgraph()` returns a
   **read-only frozen view** in networkx; mutating it without `.copy()` raises `NetworkXError`:
   ```python
   guidance_hvg = guidance.subgraph([
       *rna.var_names[rna.var["highly_variable"]],
       *atac.var_names[atac.var["highly_variable"]],
   ]).copy()
   ```
6. GPU control: `SCGLUEModel` has no `use_gpu` constructor parameter; GPU selection is via
   the environment. Disable GPU by setting `os.environ["CUDA_VISIBLE_DEVICES"] = ""` before
   training when `use_gpu=False`. Train with correct kwarg routing:
   ```python
   model_dir = str(output_dir / "glue_model") if output_dir else None
   model = scglue.models.fit_SCGLUE(
       {"rna": rna, "atac": atac},
       guidance_hvg,
       init_kws={"latent_dim": n_latent, "random_seed": random_seed},
       fit_kws={"max_epochs": n_epochs, "directory": model_dir},
   )
   ```
   Note: `fit_SCGLUE` parameter names are `latent_dim` (not `n_latent`) and `max_epochs`
   (not `n_epochs`); these are routed via `init_kws` and `fit_kws` respectively.
7. Extract cell embeddings per modality:
   ```python
   adata.obsm[embedding_key]  = model.encode_data("rna",  rna)   # (n_rna_cells  × n_latent)
   atac.obsm[embedding_key]   = model.encode_data("atac", atac)  # (n_atac_cells × n_latent)
   ```
8. Extract feature embeddings — `encode_graph()` returns a **single flat array** indexed by
   the graph's node ordering, not pre-split by modality. Must be manually aligned to each
   AnnData's `var_names`:
   ```python
   import numpy as np
   feat_embs  = model.encode_graph(guidance_hvg)           # (n_hvg_nodes, n_latent)
   vertices   = list(guidance_hvg.nodes)
   vertex_idx = {v: i for i, v in enumerate(vertices)}

   # RNA: allocate full-var array; fill HVG rows; NaN for non-HVG
   rna_emb = np.full((rna.n_vars, feat_embs.shape[1]), np.nan)
   for j, g in enumerate(rna.var_names):
       if g in vertex_idx:
           rna_emb[j] = feat_embs[vertex_idx[g]]
   rna.varm[embedding_key] = rna_emb

   # ATAC: same pattern
   atac_emb = np.full((atac.n_vars, feat_embs.shape[1]), np.nan)
   for j, p in enumerate(atac.var_names):
       if p in vertex_idx:
           atac_emb[j] = feat_embs[vertex_idx[p]]
   atac.varm[embedding_key] = atac_emb
   ```
9. Compute integration consistency score — function lives in `scglue.models.dx`, not
   `scglue.models`; returns a **DataFrame** (one row per metacell resolution), not a scalar:
   ```python
   from scglue.models.dx import integration_consistency
   consistency_df = integration_consistency(
       model, {"rna": rna, "atac": atac}, guidance_hvg
   )
   # DataFrame has columns: n_meta, consistency (confirmed from SCGLUE API)
   adata.uns["glue_consistency_score"] = float(consistency_df["consistency"].mean())
   adata.uns["glue_consistency_df"]    = consistency_df.to_dict()
   ```
   A mean score > 0.05 indicates reliable integration.
10. Write updated ATAC h5ad back to disk. When `output_dir` is provided, write to a new file to
    preserve the original; when `output_dir=None`, overwrite in-place and update the pointer:
    ```python
    atac_out_path = (output_dir / "atac_glue.h5ad") if output_dir else Path(atac_h5ad_path)
    atac.write_h5ad(atac_out_path)
    adata.uns["atac_h5ad_path"] = str(atac_out_path)  # update pointer if path changed
    ```
11. Store model path in `adata.uns["glue_model_path"]`

**Outputs:**
- `adata.obsm["X_glue"]`: (n_cells × n_latent) joint embedding for RNA cells
- `adata.varm["X_glue"]`: (n_genes × n_latent) gene feature embeddings
- `adata.uns["glue_model_path"]`: path to saved `.dill` model
- `adata.uns["glue_consistency_score"]`: float (mean over metacell resolutions); > 0.05 indicates reliable integration
- `adata.uns["glue_consistency_df"]`: full consistency DataFrame as dict (for plotting per resolution)
- `adata.uns["embedding"]`: standard wiring dict with `"obsm_key": "X_glue"` (auto-wires
  clustering/UMAP tools downstream)
- ATAC h5ad on disk updated with `obsm["X_glue"]` and `varm["X_glue"]`

**Auto-wiring output context:**
```python
adata.uns["embedding"] = {
    "method": "glue",
    "n_latent": n_latent,
    "batch_key": batch_key,
    "obsm_key": embedding_key,        # "X_glue"
}
```
DagExecutor reads this into `embedding_key` → passes to downstream clustering/UMAP tools.

**Key dependencies:** `scglue`, `dill`; no new refs entries needed.

**Comparison to existing embed tools:**

| Tool | Paired required? | Latent space | Feature embeddings |
|---|---|---|---|
| `multi_embed_wnn` | Yes | WNN graph (not latent) | No |
| `multi_embed_mofa` | Yes | MOFA factors | Loadings only |
| `multi_embed_multivi` | Yes | VAE latent | No |
| **`multi_embed_glue`** | **No** | VAE latent (graph-guided) | **Yes** (`varm["X_glue"]`) |

---

### 3. `multi_peak2gene_glue`

**File:** `backend/tools/multi/grn/peak2gene_glue.py`

**Purpose:** Compute peak-to-gene regulatory links using cosine similarity between GLUE feature
embeddings. Unlike expression/accessibility correlation methods, this operates entirely in the
learned latent space — robust to zero-inflation and usable on unpaired data.

**Inputs (via `run()` signature):**
```python
def run(
    adata,                                  # RNA AnnData with varm["X_glue"]
    *,
    atac_h5ad_path: str | Path | None = None,   # ATAC AnnData with varm["X_glue"]
    glue_graph_path: str | Path | None = None,  # guide edges constrain candidate pairs
    cosine_threshold: float = 0.15,         # minimum cosine similarity to report link
    n_top_peaks_per_gene: int | None = 10,  # optional: keep only top-N peaks per gene
    output_dir: Path | None = None,
) -> object:
```

**Algorithm:**
1. Load ATAC AnnData; read `varm["X_glue"]` from both
2. Load guidance graph to constrain candidate pairs (avoids O(n_genes × n_peaks) computation)
3. Build name→integer-index lookup dicts (required because `varm` is a numpy array, not a
   named dict). Filter to features with valid (non-NaN) embeddings before iteration —
   non-HVG features were filled with NaN in `multi_embed_glue` Step 8; computing cosine
   against a NaN row produces NaN which silently passes or drops comparisons:
   ```python
   import numpy as np
   rna_idx  = {g: i for i, g in enumerate(rna.var_names)}
   atac_idx = {p: i for i, p in enumerate(atac.var_names)}
   rna_valid  = set(rna.var_names[~np.isnan(rna.varm["X_glue"]).any(axis=1)])
   atac_valid = set(atac.var_names[~np.isnan(atac.varm["X_glue"]).any(axis=1)])

   # TSS approximated as chromStart for all genes.
   # get_gene_annotation() adds only chrom/chromStart/chromEnd — no strand column.
   # distance_to_tss is therefore approximate for minus-strand genes (~50% of genes,
   # where true TSS is chromEnd). This is a known limitation; accurate strand-aware
   # distances require supplementing rna.var from the GTF separately.
   rows = []
   for gene, peak in guidance.edges():
       if gene not in rna_valid or peak not in atac_valid:
           continue
       g_emb = rna.varm["X_glue"][rna_idx[gene]]
       p_emb = atac.varm["X_glue"][atac_idx[peak]]
       cos   = np.dot(g_emb, p_emb) / (np.linalg.norm(g_emb) * np.linalg.norm(p_emb))
       tss      = int(rna.var.loc[gene, "chromStart"])   # approximation; see note above
       peak_mid = (int(atac.var.loc[peak, "chromStart"]) + int(atac.var.loc[peak, "chromEnd"])) // 2
       rows.append({
           "gene": gene, "peak": peak,
           "cosine_similarity": float(cos),
           "chrom": atac.var.loc[peak, "chrom"],
           "distance_to_tss": peak_mid - tss,
       })
   links_df = pd.DataFrame(rows)
   ```
4. Apply `cosine_threshold` filter on `links_df`
5. If `n_top_peaks_per_gene` set: keep top-N peaks per gene by cosine score
6. Produce final DataFrame: columns `["gene", "peak", "cosine_similarity", "chrom", "distance_to_tss"]`
7. Write CSV only if `output_dir` is provided (guard against `TypeError` on `None / "..."`):
   ```python
   adata.uns["glue_peak2gene_links"] = links_df
   if output_dir:
       links_path = output_dir / "glue_peak2gene_links.csv"
       links_df.to_csv(links_path, index=False)
       adata.uns["glue_peak2gene_path"] = str(links_path)
   # When output_dir=None, links exist only in adata.uns["glue_peak2gene_links"]
   ```

**Outputs:**
- `adata.uns["glue_peak2gene_links"]`: filtered DataFrame of peak-gene links (always present)
- `adata.uns["glue_peak2gene_path"]`: path to CSV on disk (only set when `output_dir` provided)

**Distinction from existing peak-to-gene tools:**

| Tool ID | Method | Requires paired cells? | Uses GLUE? |
|---|---|---|---|
| `atac_peak2gene_correlation` | Pearson correlation (expr × access) | Yes | No |
| `atac_peak2gene_cicero` | Co-accessibility | No (ATAC only) | No |
| `atac_peak2gene_linkage` | Genomic proximity only | No | No |
| `multi_grn_peak_to_gene` | RF importance + Spearman (SCENIC+) | Yes | No |
| **`multi_peak2gene_glue`** | Cosine similarity in latent space | **No** | **Yes** |

---

### 4. `multi_grn_glue`

**File:** `backend/tools/multi/grn/glue.py`

**Purpose:** Infer a TF-gene regulatory network using the GLUE feature embedding space as a
bridge: TF motif matches → peaks (via motif scanning), peaks → genes (via GLUE cosine similarity).
This produces a ranked TF-gene edge list comparable to, but mechanistically distinct from,
SCENIC+ eRegulons.

**Inputs (via `run()` signature):**
```python
def run(
    adata,                                      # RNA AnnData with varm["X_glue"]
    *,
    atac_h5ad_path: str | Path | None = None,   # ATAC AnnData with varm["X_glue"]
    glue_graph_path: str | Path | None = None,  # guidance graph for regulatory_inference skeleton
    motif_db: str = "jaspar_hg38",              # refs store JASPAR BED key
    genome_assembly: str = "hg38",              # "hg38" or "mm10"
    tf_list: str | None = "human_tfs",          # optional secondary TF filter
    reginf_qval: float = 0.05,                  # q-value threshold for gene→peak links
    output_dir: Path | None = None,
) -> object:
```

Note: `peak_gene_links_key` is **not** a parameter. `multi_grn_glue` does not consume
`multi_peak2gene_glue` output — `cis_regulatory_ranking()` requires a NetworkX Graph from
`regulatory_inference()`, not a cosine-similarity DataFrame. The tools are independent
branches from `multi_embed_glue`.

**Algorithm:**

This tool follows the SCGLUE Stage 3 regulatory inference tutorial exactly:
`regulatory_inference()` → `window_graph()` → `cis_regulatory_ranking()`.

1. Load RNA and ATAC AnnData; resolve `varm["X_glue"]` from both; load guidance graph
2. Load and parse JASPAR BED file via `scglue.genomics.read_bed()`:
   ```python
   jaspar_bed_path = refs.get_motif_bed(motif_db, genome_assembly)
   motif_bed = scglue.genomics.read_bed(jaspar_bed_path)
   # motif_bed: scglue.genomics.Bed object; columns: chrom, chromStart, chromEnd, name (TF name)
   ```
3. Compute gene↔peak regulatory links via `regulatory_inference()` — this is the **required**
   source for `cis_regulatory_ranking()`'s first argument. It uses the GLUE feature embeddings
   (not raw expression/accessibility) and returns a NetworkX Graph with edge attributes
   `score`, `pval`, `qval`:
   ```python
   import numpy as np
   features  = list(rna.var_names) + list(atac.var_names)
   feat_embs = np.vstack([rna.varm["X_glue"], atac.varm["X_glue"]])

   reginf = scglue.genomics.regulatory_inference(
       features,
       feat_embs,
       skeleton=guidance_hvg,   # guidance graph HVG subgraph restricts candidate pairs
       random_state=0,
   )
   # Filter to high-confidence gene→peak links by q-value
   gene2peak = reginf.edge_subgraph(
       [e for e, attr in dict(reginf.edges).items() if attr["qval"] < reginf_qval]
   ).copy()
   ```
4. Build peak→TF graph. `scglue.genomics.Bed` object is required as the LEFT argument to
   `window_graph` (plain `pd.DataFrame` raises `AttributeError`). Peaks filtered to valid
   (non-NaN) embeddings only. `window_size=0` (third positional argument). No `attr_fn`:
   ```python
   peaks    = atac.var_names[~np.isnan(atac.varm["X_glue"]).any(axis=1)]
   peak_bed = scglue.genomics.Bed(atac.var.loc[peaks])  # Bed subclass required

   peak2tf = scglue.genomics.window_graph(
       peak_bed,        # LEFT: Bed object of ATAC peaks
       motif_bed,       # RIGHT: Bed object from read_bed()
       0,               # window_size — third positional arg (exact overlap)
       right_sorted=True,
   )
   # peak2tf: directed Graph with edges peak → TF
   ```
5. Determine valid TF set and filter `peak2tf`. Primary filter: BED `name` values intersected
   with `rna.var_names` (TF nodes not in RNA cannot be scored). Secondary: optional curated
   list. Filter `peak2tf` immediately to remove unexpressed TF nodes from the output:
   ```python
   import pandas as pd
   genes = rna.var_names
   tfs   = pd.Index(motif_bed["name"]).intersection(rna.var_names)
   if tf_list:
       tfs = tfs.intersection(set(refs.get_tf_list(tf_list)))

   # Remove unexpressed TFs from peak2tf to prevent inflated GRN output
   peak2tf = peak2tf.edge_subgraph(
       [e for e in peak2tf.edges if e[1] in set(tfs)]
   ).copy()
   ```
6. Score with `cis_regulatory_ranking()` — uses stratified random sampling for peak-length bias
   correction; first argument is the NetworkX Graph from Step 3, not a DataFrame:
   ```python
   gene2tf_rank = scglue.genomics.cis_regulatory_ranking(
       gene2peak,   # NetworkX Graph from regulatory_inference() — NOT a DataFrame
       peak2tf,
       genes, peaks, tfs,
       region_lens=atac.var.loc[peaks, "chromEnd"] - atac.var.loc[peaks, "chromStart"],
       random_state=0,
   )
   # gene2tf_rank: genes × TFs ranking matrix
   ```
7. Convert ranking matrix to flat edge list and save:
   ```python
   grn_df = (gene2tf_rank
       .stack()
       .reset_index()
       .rename(columns={"level_0": "target_gene", "level_1": "TF", 0: "regulatory_rank"})
   )
   ```
8. Save GRN edges as CSV: columns `["TF", "target_gene", "regulatory_rank"]`
9. Return `GRN` dataclass (consistent with `rna_grn_grnboost2`, `multi_grn_scenicplus` output)

**Outputs:**
- `adata.uns["glue_grn"]`: metadata dict
- Returns `GRN` dataclass with `n_tfs`, `n_targets`, `n_edges`, `edges_path`

**Distinction from existing GRN tools:**

| Tool ID | TF → peak method | Peak → gene method | Requires paired cells? |
|---|---|---|---|
| `rna_grn_grnboost2` | N/A (RNA only) | N/A | No |
| `rna_grn_scenic_pyscenic` | Motif scan | N/A | No |
| `multi_grn_scenicplus` | pycistarget cisTarget | RF importance (SCENIC+) | Yes |
| **`multi_grn_glue`** | JASPAR BED overlap (`window_graph`) | GLUE cosine similarity | **No** |

`multi_grn_glue` produces TF-gene networks from unpaired data where SCENIC+ cannot run.

**Key dependencies:** `scglue` (all graph operations native); uses existing `motifs` and
`tf_list` refs store categories; **requires JASPAR BED refs entries** (see Refs Store below).

---

## DAG Execution Order

### Full GLUE pipeline (unpaired RNA + ATAC)

```
[RNA branch]
rna_qc_basic
  → rna_normalize_log1p
    → rna_feature_seurat_v3   (HVG; n_top_genes=2000, seurat_v3)
      → rna_embed_pca         (n_comps=100; encoder input for GLUE)

[ATAC branch]
atac_qc_basic
  → atac_embed_lsi            (n_components=100; encoder input for GLUE)

[GLUE-specific]
multi_preprocess_glue_graph   (RNA + ATAC → guidance.graphml.gz)
  → multi_embed_glue          (trains model; produces X_glue + varm["X_glue"])
    → multi_cluster_leiden    (on X_glue; auto-wired via adata.uns["embedding"])
    → rna_embed_umap          (on X_glue; auto-wired)

[Optional downstream — both branch independently from multi_embed_glue]
multi_embed_glue → multi_peak2gene_glue    (cosine similarity links; user-facing output)
multi_embed_glue → multi_grn_glue          (calls regulatory_inference() internally)
multi_preprocess_glue_graph → multi_grn_glue   (guidance graph as skeleton)

Note: multi_peak2gene_glue and multi_grn_glue are independent. multi_grn_glue does NOT
consume multi_peak2gene_glue output — it calls regulatory_inference() directly on
varm["X_glue"] embeddings. Running multi_peak2gene_glue first is optional.
```

### Minimal DAG plan JSON skeleton

```json
{
  "input_h5ad_path": "<rna.h5ad>",
  "layers": [
    {"tool": "rna_qc_basic",           "variants": [{"params": {}}]},
    {"tool": "rna_normalize_log1p",    "variants": [{"params": {}}]},
    {"tool": "rna_feature_seurat_v3",  "variants": [{"params": {"n_top_genes": 2000}}]},
    {"tool": "rna_embed_pca",          "variants": [{"params": {"n_comps": 100}}]},
    {"tool": "multi_preprocess_glue_graph", "variants": [
      {"params": {"genome_assembly": "hg38"}}
    ]},
    {"tool": "multi_embed_glue", "variants": [
      {"params": {"n_latent": 50, "n_epochs": 500}},
      {"params": {"n_latent": 30, "n_epochs": 500}}
    ]},
    {"tool": "multi_cluster_leiden", "variants": [
      {"params": {"resolution": 0.8}},
      {"params": {"resolution": 1.2}}
    ]}
  ],
  "objective_name": "silhouette",
  "evaluation": {
    "metrics": ["silhouette", "ilisi", "clisi"]
  }
}
```

The ATAC branch (QC → LSI) runs separately and its output h5ad path is registered in
`adata.uns["atac_h5ad_path"]` before the GLUE graph step.

---

## File Layout

```
backend/tools/multi/
├── preprocess/                         ← new directory
│   ├── __init__.py
│   └── glue_graph.py                   → multi_preprocess_glue_graph
├── embed/
│   ├── wnn.py                          (existing)
│   ├── mofa.py                         (existing)
│   ├── multivi.py                      (existing)
│   └── glue.py                         → multi_embed_glue  [NEW]
└── grn/
    ├── peak_to_gene.py                 (existing, SCENIC+)
    ├── pycistarget.py                  (existing)
    ├── scenicplus.py                   (existing)
    ├── scenicplus_aucell.py            (existing)
    ├── peak2gene_glue.py               → multi_peak2gene_glue  [NEW]
    └── glue.py                         → multi_grn_glue         [NEW]
```

Registry auto-discovers all `.py` files; no registration code changes needed.

---

## Refs Store: Required Entries

Most references already exist. `multi_grn_glue` uses pre-computed JASPAR BED files for motif
overlap (no FASTA genome files needed) — only the BED entries below must be added to the
manifest before `multi_grn_glue` can be implemented.

### Existing (no change needed)

| Ref key | Category | Used by |
|---|---|---|
| `gencode_v44_hg38` | `annotation` | `multi_preprocess_glue_graph` (human GTF) |
| `gencode_vM33_mm10` | `annotation` | `multi_preprocess_glue_graph` (mouse GTF) |
| `human_tfs` / `mouse_tfs` | `tf_list` | `multi_grn_glue` (secondary TF filter) |

Note: the existing `motifs` category entries (JASPAR PWM objects for pycistarget/pyjaspar) are
**not** used by `multi_grn_glue`. That tool uses pre-computed JASPAR genome-wide BED files
(motif hit coordinates), not PWM matrices.

### New entries required for `multi_grn_glue`

`multi_grn_glue` uses the SCGLUE-native `window_graph` approach — it requires pre-computed
JASPAR BED files mapping TF motif hit coordinates to the reference genome, **not** raw genome
FASTA files. No FASTA or sequence-scanning library is needed.

| Ref key | Category | Source | Used by |
|---|---|---|---|
| `jaspar_hg38_bed` | `motifs` | JASPAR website (genome-wide motif BED for hg38) | `multi_grn_glue` (TF→peak overlap) |
| `jaspar_mm10_bed` | `motifs` | JASPAR website (genome-wide motif BED for mm10) | `multi_grn_glue` (TF→peak overlap) |

Add to `backend/refs/manifest.py` as `ResourceSpec` entries with `category="motifs"` and a
BED file loader. `multi_grn_glue` calls `refs.get_motif_bed(motif_db, genome_assembly)`.

The refs store accessor `get_motif_bed(name, assembly)` may need to be added to
`backend/refs/store.py` (analogous to existing `get_motifs(db)` for PWM objects).

**Implementation gate:** `multi_grn_glue` cannot be implemented until these BED entries and
the `get_motif_bed()` accessor are added. The other three tools are unblocked.

---

## Result Types

No new dataclasses needed. `multi_grn_glue` returns the existing `GRN` dataclass from
`backend/types.py`. All intermediate products are stored in `adata.uns` as dicts or DataFrames,
consistent with every other tool in the codebase.

The only non-standard artifact is `varm["X_glue"]` (feature embeddings on `var` axis). This is
an `ndarray` in AnnData's `varm` slot and persists naturally through `.h5ad` save/load — no
special handling required.

---

## Implementation Order

Implement in this sequence (each step unblocks the next):

| # | Tool | Blocks |
|---|---|---|
| 1 | `multi_preprocess_glue_graph` | Everything GLUE |
| 2 | `multi_embed_glue` | All downstream GLUE tools |
| 3 | `multi_peak2gene_glue` | `multi_grn_glue` |
| 4 | `multi_grn_glue` | — |

Steps 3 and 4 are optional for the core integration use-case (cell embedding + clustering).
Most users will stop at step 2 and run existing clustering/UMAP tools downstream.

---

## Integration with Agent System

- **ToolConsultant**: GLUE tools are valid `multi`-stage tools discoverable by the agent. The
  consultant should prefer `multi_embed_glue` over `multi_embed_wnn`/`multi_embed_multivi` when
  the user query mentions unpaired data, cross-study integration, or multi-omics without
  simultaneous measurement.

- **ScientistPanel**: Should understand that GLUE produces feature embeddings (`varm["X_glue"]`)
  that enable downstream regulatory inference — a capability absent from WNN/MOFA/MultiVI.

- **DagExecutor auto-wiring**: `multi_embed_glue` writes `adata.uns["embedding"]["obsm_key"] =
  "X_glue"`. DagExecutor injects this as `embedding_key` into any downstream tool that declares
  `embedding_key` in its signature — same mechanism used for PCA, LSI, scVI, etc.

- **Integration consistency score** (`adata.uns["glue_consistency_score"]`) is a mean float
  derived from `scglue.models.dx.integration_consistency()` (which returns a DataFrame of
  per-resolution scores). It is not one of the four standard eval tool metrics, but the
  AnalyzerPanel should treat a mean score > 0.05 as indicating successful integration. The
  full per-resolution DataFrame is preserved in `adata.uns["glue_consistency_df"]` for plotting.
