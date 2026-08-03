# GLUE Implementation Plan — Review

**Plan file:** `plans/glue_plan.md`  
**Reviewer:** Claude (computational biology code review)  
**API reference:** https://scglue.readthedocs.io/en/latest/

---

## Review History

| Pass | Date | Issues Found | Issues Resolved |
|---|---|---|---|
| Pass 1 | 2026-05-15 | 10 (3 critical, 4 moderate, 3 minor) | 10 |
| Pass 2 | 2026-05-15 | 8 new (1 critical, 4 moderate, 3 minor) | 18/18 |
| Pass 3 | 2026-05-15 | 5 new (1 critical, 3 moderate, 1 minor) | 23/23 |
| Pass 4 | 2026-05-15 | 6 new (1 critical, 3 moderate, 2 minor) | 29/29 |
| Pass 5 | 2026-05-15 | 5 new (3 critical, 2 moderate) | 34/34 |
| Pass 6 | 2026-05-15 | 5 new (3 critical, 2 moderate) | 39/39 |
| Pass 7 | 2026-05-15 | 3 new (0 critical, 2 moderate, 1 minor) | 39/39 from Pass 6 |

---

## Summary

The overall architecture (4 tools, DAG ordering, dual-AnnData convention, `varm["X_glue"]` feature embeddings, auto-wiring via `adata.uns["embedding"]`) is well-designed and correctly motivated. Pass 1 verified all SCGLUE function signatures against the official documentation and found 10 issues (all resolved). Pass 2 found 8 new issues (all resolved): `gene_region="promoter_only"` invalid, `output_dir=None` path crashes, NaN embedding guard missing, motif scanning unspecified, and housekeeping items. Pass 3 found 5 new issues (all resolved): guidance graph lost when `output_dir=None`, `distance_to_tss` undocumented, MOODS placeholder replaced with SCGLUE-native BED approach, failure mode comment wrong, and `gtf_by` missing. Pass 4 found 6 new issues (all resolved): `read_bed()` missing, `attr_fn` unspecified, TF filtering underdocumented, consistency column hedge, refs store label wrong, edge direction undocumented. Pass 5 found 5 new issues from deeper tutorial verification: three critical (`window_graph` arguments are reversed — peaks must be left arg not motifs; entire scoring algorithm is wrong — plan uses `compose_multigraph` + manual traversal but tutorial uses `cis_regulatory_ranking()`; `rna.var["strand"]` column never exists after `get_gene_annotation()` so TSS is always wrong for - strand genes), and two moderate (`attr_fn` added in Pass 4 is unnecessary as tutorial uses no `attr_fn`; `scglue.genomics.regulatory_inference()` high-level function exists and should be evaluated). Pass 6 found 5 new issues from precise API verification of the corrected Pass 5 code: three critical (the `gene2peak` input to `cis_regulatory_ranking()` must be a NetworkX Graph from `regulatory_inference()` — not the `links_df` DataFrame output of `multi_peak2gene_glue`, which is incompatible and raises `TypeError`; the peak argument to `window_graph` must be a `scglue.genomics.Bed` object, not a plain DataFrame — a `Bed` wrapping `atac.var` is required; this creates a fundamental DAG dependency mismatch — `multi_grn_glue` cannot consume `multi_peak2gene_glue` output and must call `regulatory_inference()` directly, requiring DAG redesign), and two moderate (`peak2tf` missing an edge subgraph filter to restrict to TFs expressed in RNA after `window_graph`; the Refs Store intro paragraph still mentions "FASTA files" — stale from before the BED pivot in Pass 3). Pass 7 verified the corrected Pass 6 code against the official SCGLUE regulatory inference tutorial and found 3 issues (0 critical, 2 moderate, 1 minor): `genes` passed to `cis_regulatory_ranking()` uses all of `rna.var_names` but the tutorial restricts to HVG genes only; the Implementation Order table still lists `multi_peak2gene_glue` as blocking `multi_grn_glue` despite the DAG having been corrected; and `n_samples` from `cis_regulatory_ranking()` is not exposed in the tool signature.

---

## Pass 1 Issues — All Resolved

| # | Tool | Issue | Fix Applied |
|---|---|---|---|
| 1 | `multi_preprocess_glue_graph` | `scglue.data.get_peak_annotation()` does not exist | Manual string split on `var_names` with `chr:start-end` assertion |
| 2 | `multi_embed_glue` | `fit_SCGLUE()` does not accept `n_latent`/`n_epochs` directly | Routed through `init_kws={"latent_dim": ...}` and `fit_kws={"max_epochs": ...}` |
| 3 | `multi_embed_glue` | `encode_graph()` returns single flat array; varm split undocumented | `vertex_idx` dict pattern for splitting into `rna.varm` / `atac.varm` with NaN fill |
| 4 | `multi_embed_glue` | `batch_key` not forwarded to `configure_dataset(use_batch=...)` | `use_batch=batch_key` added to both RNA and ATAC configure calls |
| 5 | `multi_embed_glue` | `integration_consistency` in wrong module; returns DataFrame not float | Import from `scglue.models.dx`; `.mean()` for scalar + full dict stored |
| 6 | `multi_embed_glue` | `use_gpu` not a param of `SCGLUEModel` | Documented as `os.environ["CUDA_VISIBLE_DEVICES"] = ""` side effect |
| 7 | `multi_preprocess_glue_graph` | Manual HVG propagation duplicated built-in; `gene_region`/`promoter_len` not exposed | Removed manual step; `propagate_highly_variable=use_highly_variable` used; params added to signature |
| 8 | `multi_embed_glue` | `guidance.subgraph()` returns read-only view | `.copy()` added |
| 9 | `multi_preprocess_glue_graph` | `nx.write_graphml_lxml()` requires optional `lxml` | Changed to `nx.write_graphml()` |
| 10 | Both | `rna_anchored_guidance_graph` returns `MultiDiGraph`; type implications undocumented | Note added; `check_graph()` call documented |

---

## Pass 2 Issues — Open

---

### Critical

#### 1. `multi_preprocess_glue_graph` — `gene_region="promoter_only"` is not a valid value

The updated signature documents `gene_region` as `"combined" (promoter + body) or "promoter_only"`. Verified from the SCGLUE API: the valid values for `rna_anchored_guidance_graph(gene_region=...)` are `{"gene_body", "promoter", "combined"}`. The string `"promoter_only"` does not exist and will raise a `ValueError`. The correct alternative to `"combined"` is `"promoter"`:

```python
gene_region: str = "combined",  # "combined" (promoter + body), "promoter" (upstream window only), or "gene_body"
```

Update the docstring and any user-facing wiki parameter description accordingly.

---

### Moderate

#### 2. `multi_preprocess_glue_graph` and `multi_peak2gene_glue` — `output_dir / "..."` unguarded when `output_dir=None`

Both tools declare `output_dir: Path | None = None` but perform path operations without guarding:

- `multi_preprocess_glue_graph` Step 6: `nx.write_graphml(guidance, str(output_dir / "guidance.graphml.gz"))` — crashes with `TypeError` when `output_dir=None`
- `multi_peak2gene_glue` Step 7: `output_dir / "glue_peak2gene_links.csv"` — same issue

The fix in `multi_embed_glue` (`model_dir = str(output_dir / "glue_model") if output_dir else None`) shows the correct pattern. Apply consistently:

```python
# multi_preprocess_glue_graph
if output_dir:
    nx.write_graphml(guidance, str(output_dir / "guidance.graphml.gz"))
    adata.uns["glue_graph_path"] = str(output_dir / "guidance.graphml.gz")

# multi_peak2gene_glue
if output_dir:
    links_path = output_dir / "glue_peak2gene_links.csv"
    links_df.to_csv(links_path, index=False)
    adata.uns["glue_peak2gene_path"] = str(links_path)
```

Also document what happens when `output_dir=None` — graph and link table exist only in memory/`adata.uns`.

---

#### 3. `multi_peak2gene_glue` — non-HVG features have `NaN` embeddings; cosine similarity silently corrupts results

`varm["X_glue"]` was populated with `np.nan` for all features not in the HVG-subsetted guidance graph. The full guidance graph (used here to constrain candidate pairs) includes edges to non-HVG peaks and genes. Computing cosine similarity against a NaN row produces NaN — which pandas comparisons like `NaN < threshold` silently evaluate to `False`, making the filter appear to work while silently dropping valid-looking pairs. Fix by filtering to only features with valid embeddings before computing:

```python
rna_valid  = set(rna.var_names[~np.isnan(rna.varm["X_glue"]).any(axis=1)])
atac_valid = set(atac.var_names[~np.isnan(atac.varm["X_glue"]).any(axis=1)])

rna_idx  = {g: i for i, g in enumerate(rna.var_names)}
atac_idx = {p: i for i, p in enumerate(atac.var_names)}

rows = []
for gene, peak in guidance.edges():
    if gene not in rna_valid or peak not in atac_valid:
        continue
    g_emb = rna.varm["X_glue"][rna_idx[gene]]
    p_emb = atac.varm["X_glue"][atac_idx[peak]]
    cos   = np.dot(g_emb, p_emb) / (np.linalg.norm(g_emb) * np.linalg.norm(p_emb))
    rows.append({"gene": gene, "peak": peak, "cosine_similarity": cos})
```

---

#### 4. `multi_grn_glue` — motif scanning implementation entirely absent

Step 4 states "Scan ATAC peaks for TF motif matches → TF-peak association scores" with no library, no FASTA genome reference, and no scanning tool specified. This step cannot be implemented as written. The plan must specify:

1. **FASTA genome source** — peak sequences must be extracted from a reference genome FASTA (`hg38.fa` / `mm10.fa`). These are not currently in the refs store. Add `hg38_fasta` and `mm10_fasta` entries, or document how to derive the FASTA path from the existing `genome_assembly` parameter.

2. **Sequence extraction tool** — `pybedtools.BedTool.sequence()` or `pysam.FastaFile` for extracting peak sequences.

3. **Motif scanning library** — e.g., MOODS (`moods-python`) or `pyjaspar` + FIMO. Document which is used, what score threshold applies, and how TF-peak p-values are computed.

Skeleton that must be documented:

```python
from pybedtools import BedTool
# 1. Extract peak sequences from FASTA
peaks_bed = BedTool.from_dataframe(atac.var[["chrom", "chromStart", "chromEnd"]])
peak_seqs = peaks_bed.sequence(fi=refs.get_fasta(genome_assembly))
# 2. Scan with JASPAR PWMs — library TBD (MOODS, FIMO, etc.)
```

Flag in the plan that `multi_grn_glue` requires a new refs store entry for genome FASTA and a defined scanning library before it can be implemented.

---

#### 5. `multi_embed_glue` — `consistency_df["consistency"]` column name unverified

The plan uses `float(consistency_df["consistency"].mean())` but the exact DataFrame column name returned by `scglue.models.dx.integration_consistency()` was not confirmed from official docs. If the column is named differently (e.g., `"FOSCTTM"` or indexed differently), this raises `KeyError`. Add a defensive check or document the column name with a source reference:

```python
consistency_df = integration_consistency(model, {"rna": rna, "atac": atac}, guidance_hvg)
# Confirm column name at runtime
score_col = "consistency" if "consistency" in consistency_df.columns else consistency_df.columns[-1]
adata.uns["glue_consistency_score"] = float(consistency_df[score_col].mean())
```

---

### Minor

#### 6. `multi_peak2gene_glue` — `varm["X_glue"][gene]` indexing by gene name not shown

Step 3 describes computing cosine similarity between `rna.varm["X_glue"][gene]` and `atac.varm["X_glue"][peak]`. `varm` is a numpy array indexed by integer position, not by feature name. The plan gives no implementation for this lookup. Must build a name→index dict:

```python
rna_idx  = {g: i for i, g in enumerate(rna.var_names)}
atac_idx = {p: i for i, p in enumerate(atac.var_names)}
# Access: rna.varm["X_glue"][rna_idx[gene]]
```

---

#### 7. `multi_embed_glue` — ATAC h5ad write-back path undocumented when `output_dir=None`

Step 10 says "Write updated ATAC h5ad back to disk" but does not specify the path. When `output_dir=None`, the only sensible option is overwriting the original `atac_h5ad_path` in-place. The plan must document this and update the pointer:

```python
atac_out_path = (output_dir / "atac_glue.h5ad") if output_dir else atac_h5ad_path
atac.write_h5ad(atac_out_path)
adata.uns["atac_h5ad_path"] = str(atac_out_path)  # update pointer if path changed
```

---

#### 8. `multi_embed_glue` — `configure_dataset(use_layer="counts")` silently fails if layer absent

Step 4 calls `scglue.models.configure_dataset(rna, ..., use_layer="counts")`, assuming `adata.layers["counts"]` exists. If a user provides a pre-normalized AnnData without a raw counts layer, `configure_dataset` may silently fall back to `.X` (already log-normalized), causing the NB decoder to model log-normalized values as raw counts — a silent numerical error. Add a runtime assertion:

```python
assert "counts" in adata.layers, (
    "RNA adata must have layers['counts'] (raw integer counts). "
    "Ensure rna_normalize_log1p ran before multi_embed_glue."
)
```

---

## Pass 3 Issues — Open

---

### Critical

#### 1. `multi_preprocess_glue_graph` + `multi_embed_glue` — guidance graph is lost when `output_dir=None`; no in-memory handoff mechanism exists

When `output_dir=None`, the plan stores `adata.uns["glue_graph_path"] = None` and comments "downstream tools must receive the graph object directly." There is no mechanism for this. The `guidance` graph object exists only in the local scope of `multi_preprocess_glue_graph.run()` and is discarded on return. `multi_embed_glue` Step 2 attempts to resolve from `glue_graph_path` param or `adata.uns["glue_graph_path"]` — both `None` — and then has no graph to load.

AnnData's `.uns` cannot reliably round-trip `networkx.MultiDiGraph` through `.h5ad` serialization (h5py cannot store graph objects). The correct fix is to require `output_dir` or write to a temp directory:

```python
import tempfile

graph_dir = output_dir if output_dir else Path(tempfile.mkdtemp())
graph_path = graph_dir / "guidance.graphml.gz"
nx.write_graphml(guidance, str(graph_path))
adata.uns["glue_graph_path"] = str(graph_path)
```

Remove the "downstream tools must receive the graph object directly" comment — it describes a mechanism that does not exist. Update the Outputs section to reflect that a graph file is always written.

---

### Moderate

#### 2. `multi_peak2gene_glue` — `distance_to_tss` column in output DataFrame has no documented source

Step 6 lists `["gene", "peak", "cosine_similarity", "chrom", "distance_to_tss"]` as output columns. Neither `chrom` nor `distance_to_tss` is computed anywhere in the algorithm. The cosine loop only yields `gene`, `peak`, `cosine_similarity`. Computing `distance_to_tss` requires a strand-aware TSS lookup from `rna.var` and the peak midpoint from `atac.var`:

```python
strand_col = "strand" if "strand" in rna.var.columns else None
for gene, peak in guidance.edges():
    ...
    if strand_col and rna.var.loc[gene, "strand"] == "-":
        tss = rna.var.loc[gene, "chromEnd"]
    else:
        tss = rna.var.loc[gene, "chromStart"]
    peak_mid = (atac.var.loc[peak, "chromStart"] + atac.var.loc[peak, "chromEnd"]) // 2
    distance_to_tss = int(peak_mid) - int(tss)
    rows.append({
        "gene": gene, "peak": peak,
        "cosine_similarity": float(cos),
        "chrom": atac.var.loc[peak, "chrom"],
        "distance_to_tss": distance_to_tss,
    })
```

Note: `rna.var["strand"]` is only present if `get_gene_annotation()` includes it from the GTF. Verify and add a fallback (default to `+` strand) if absent.

---

#### 3. `multi_grn_glue` — `_scan_peaks_moods()` left as placeholder; SCGLUE-native approach using `window_graph` + pre-computed JASPAR BED files is simpler and avoids all FASTA/MOODS dependencies

Verified from the SCGLUE Stage 3 regulatory inference tutorial: SCGLUE's own GRN approach does **not** scan raw FASTA sequences. Instead it:

1. Uses pre-computed JASPAR genome-wide motif BED files (TF motif hit coordinates already mapped to hg38/mm10 by JASPAR — downloadable, no FASTA needed)
2. Calls `scglue.genomics.window_graph(motif_bed, atac, window_size=0)` to create TF→peak edges where motif hits overlap peaks
3. Composes this with the RNA guidance graph via `scglue.graph.compose_multigraph()` for a TF→peak→gene bridge

The current plan's MOODS scanning approach adds `moods-python`, `pybedtools`, and genome FASTA as new dependencies, while the SCGLUE-native approach requires only pre-computed JASPAR BED files already available from the JASPAR website. The `_scan_peaks_moods()` placeholder function is still entirely undocumented.

Recommended fix — replace with SCGLUE-native approach:

```python
import scglue.genomics

# Load pre-computed JASPAR BED file (add to refs store as category="motif_bed")
jaspar_bed_path = refs.get_motif_bed(motif_db, genome_assembly)

# Build TF→peak graph from motif overlap
motif_graph = scglue.genomics.window_graph(
    jaspar_bed_path, atac,
    window_size=0,   # exact overlap: motif hit must be within peak
)

# Compose with guidance graph to bridge TF→peak→gene
combined = scglue.graph.compose_multigraph(guidance_hvg, motif_graph)
```

Update the refs store section: replace `hg38_genome`/`mm10_genome` FASTA entries with `hg38_jaspar_bed`/`mm10_jaspar_bed` motif BED entries. Remove `moods-python` and `pybedtools` from key dependencies.

---

#### 4. `multi_embed_glue` — `configure_dataset` failure mode comment is incorrect; it raises `ValueError`, not silent fallback

The plan's assertion note states the function "may silently fall back to `.X`" when `layers["counts"]` is absent. Verified from SCGLUE source: `configure_dataset` raises `ValueError` when a specified `use_layer` key does not exist — it does not fall back silently. The assertion is still good practice (provides a clearer error message sooner), but correct the comment:

```python
assert "counts" in adata.layers, (
    "RNA adata must have layers['counts'] (raw integer counts). "
    "Ensure rna_normalize_log1p ran before multi_embed_glue. "
    "configure_dataset raises ValueError if this layer is absent."  # not a silent fallback
)
```

---

### Minor

#### 5. `multi_preprocess_glue_graph` — `get_gene_annotation()` missing `gtf_by="gene_name"`; GENCODE GTF silently produces all-NaN coordinates without it

Step 2 calls `scglue.data.get_gene_annotation(rna, gtf=gtf_path, ...)` without specifying `gtf_by`. The full signature is `get_gene_annotation(adata, var_by=None, gtf=None, gtf_by=None, by_func=None)`. GENCODE GTFs contain both `gene_name` (e.g., `"TP53"`) and `gene_id` (e.g., `"ENSG00000141510.18"`). Without `gtf_by`, the merge will likely fail to match and silently produce all-NaN coordinate columns — causing `rna_anchored_guidance_graph` to connect zero peaks to any gene (no error raised).

Fix — standard RNA data uses gene symbols:

```python
scglue.data.get_gene_annotation(
    rna,
    gtf=gtf_path,
    gtf_by="gene_name",    # ADD — matches gene symbols; use "gene_id" for Ensembl ID var_names
)
# Guard against silent annotation failure
if rna.var["chrom"].isna().all():
    raise ValueError(
        "Gene annotation produced no matches. Check that gtf_by='gene_name' matches "
        "your rna.var_names format (gene symbols). Use gtf_by='gene_id' for Ensembl IDs."
    )
```

---

## Pass 4 Issues — Open

---

### Critical

#### 1. `multi_grn_glue` — `window_graph()` first argument must be a loaded DataFrame, not a file path; `scglue.genomics.read_bed()` call is missing

The plan calls:
```python
jaspar_bed_path = refs.get_motif_bed(motif_db, genome_assembly)
motif_graph = scglue.genomics.window_graph(jaspar_bed_path, atac, window_size=0)
```

Verified from the SCGLUE regulatory inference tutorial: the BED file is first loaded via `scglue.genomics.read_bed()` into a pandas DataFrame, then the DataFrame is passed to `window_graph` — not the file path:

```python
motif_bed  = scglue.genomics.read_bed(refs.get_motif_bed(motif_db, genome_assembly))
# motif_bed is a DataFrame: columns = chrom, chromStart, chromEnd, name (= TF name)
motif_graph = scglue.genomics.window_graph(motif_bed, atac, window_size=0, ...)
```

Passing a file path where a DataFrame is expected raises `TypeError` or silently produces a wrong graph. Add the `read_bed()` call explicitly before `window_graph`.

---

### Moderate

#### 2. `multi_grn_glue` — `window_graph()` `attr_fn` not specified; motif edges will lack `weight`/`sign` attributes

Confirmed signature: `window_graph(left, right, window_size, left_sorted=False, right_sorted=False, attr_fn=None)`. `attr_fn` is a callable returning edge attribute dicts. The GLUE guidance graph uses edges with `weight` and `sign` — `compose_multigraph` merges motif and guidance edges, and any scoring step that reads `edge["weight"]` will fail with `KeyError` on motif edges that have no attributes. Specify `attr_fn`:

```python
def _motif_attr_fn(left, right, dist):
    return {"weight": 1.0, "sign": 1}  # binary presence; assume activating

motif_graph = scglue.genomics.window_graph(
    motif_bed, atac,
    window_size=0,
    attr_fn=_motif_attr_fn,
)
```

---

#### 3. `multi_grn_glue` — TF filtering logic underdocumented; tutorial uses `motif_bed["name"].intersection(rna.var_names)`, not a separate `tf_list` refs entry as the primary filter

Step 7 says "Filter to TF list from refs store." The SCGLUE tutorial uses a different primary approach: TF names come from the motif BED `name` column, intersected with expressed genes in `rna.var_names`:

```python
tfs = pd.Index(motif_bed["name"]).intersection(rna.var_names)
```

This is necessary because `window_graph` node labels for TFs come from BED `name` values — only TFs also in `rna.var_names` can be scored against gene expression. The curated `tf_list` refs entry is a secondary optional filter. Document both steps in order:

```python
# Primary: restrict to TFs present in both BED and RNA
tfs = pd.Index(motif_bed["name"]).intersection(rna.var_names)

# Secondary (optional): restrict to curated TF list
if tf_list:
    known_tfs = set(refs.get_tf_list(tf_list))
    tfs = tfs.intersection(known_tfs)
```

---

#### 4. `multi_embed_glue` — `consistency_df["consistency"]` defensive column lookup should be removed; column confirmed in Pass 3

Step 9 still contains:
```python
# Column name not confirmed in docs — use defensive lookup
score_col = "consistency" if "consistency" in consistency_df.columns else consistency_df.columns[-1]
```

Pass 3 API verification confirmed the DataFrame has exactly two columns: `n_meta` and `consistency`. The comment is now wrong and the fallback adds noise. Simplify:

```python
adata.uns["glue_consistency_score"] = float(consistency_df["consistency"].mean())
adata.uns["glue_consistency_df"]    = consistency_df.to_dict()
```

---

### Minor

#### 5. Refs Store section — "Existing" table still describes `jaspar_*` as for "JASPAR PWM scanning"; wrong after BED approach

The "Existing (no change needed)" table says:
```
| `jaspar_*` (human/mouse) | `motifs` | `multi_grn_glue` (JASPAR PWM scanning) |
```

The algorithm no longer does PWM scanning. The existing PWM refs entry (if it exists for pycistarget/pyjaspar) is not used by `multi_grn_glue`. Remove this row from the "Existing" table and move to a note, or replace with the correct BED entries:

```
| `jaspar_hg38_bed` / `jaspar_mm10_bed` | `motifs` | `multi_grn_glue` (JASPAR BED overlap via window_graph) |
```

---

#### 6. `multi_grn_glue` — `compose_multigraph()` return type and edge traversal direction undocumented

`scglue.graph.compose_multigraph()` returns `MultiGraph` (directed if all inputs directed). Both `guidance` and `motif_graph` are `MultiDiGraph`, so the result is `MultiDiGraph`. The scoring step (Step 6) must follow directed edges: TF→peak (from `motif_graph`) then peak→gene (from `guidance`). Document:

```python
combined = scglue.graph.compose_multigraph(guidance, motif_graph)
# combined is MultiDiGraph (both inputs directed)
# TF→peak edges: TF node → peak node (motif_graph direction)
# peak→gene edges: peak node → gene node (guidance direction)
# Score each (TF, gene) pair by traversing: TF → peak → gene
```

Without noting direction, implementers may traverse edges backwards and produce no paths.

---

## Pass 5 Issues — All Resolved

---

### Critical

#### 1. `multi_grn_glue` — `window_graph` argument order reversed; peaks must be the LEFT argument, not motifs

The tutorial calls:
```python
peak2tf = scglue.genomics.window_graph(peak_bed, motif_bed, 0, right_sorted=True)
```

The plan calls:
```python
motif_graph = scglue.genomics.window_graph(motif_bed, atac, window_size=0, attr_fn=_motif_attr_fn)
```

Two errors: (1) LEFT and RIGHT arguments are swapped — peaks/ATAC regions must be left, motif BED must be right. (2) `window_size` is passed as the **third positional argument** in the tutorial, not as a keyword. The variable name `peak2tf` confirms the edge direction: peaks → TFs (not TF → peaks as the plan assumes). Fix:

```python
# Build ATAC BED from atac.var coordinates
atac_bed = atac.var[["chrom", "chromStart", "chromEnd"]].copy()
atac_bed.index.name = "name"  # peak names as BED name column

peak2tf = scglue.genomics.window_graph(
    atac_bed,    # peaks as LEFT argument
    motif_bed,   # JASPAR motif hits as RIGHT argument
    0,           # window_size as third positional arg
    right_sorted=True,
)
```

---

#### 2. `multi_grn_glue` — entire scoring algorithm wrong; `compose_multigraph` + manual path traversal not used in tutorial; `cis_regulatory_ranking()` is the correct scoring function

The plan Steps 5–7 use `scglue.graph.compose_multigraph(guidance, motif_graph)` followed by manual directed edge traversal. Verified from the SCGLUE regulatory inference tutorial: **`compose_multigraph` does not appear**. The actual tutorial scoring uses:

```python
gene2tf_rank_glue = scglue.genomics.cis_regulatory_ranking(
    gene2peak,    # peak-gene links DataFrame (from multi_peak2gene_glue output)
    peak2tf,      # peak-to-TF graph (from window_graph)
    genes, peaks, tfs,
    region_lens=atac.var.loc[peaks, "chromEnd"] - atac.var.loc[peaks, "chromStart"],
    random_state=0,
)
```

`cis_regulatory_ranking()` uses stratified random sampling to compute enrichment scores accounting for peak-length bias — not simple cosine aggregation. The plan's Steps 5–7 must be replaced with this call. The output is a ranking matrix (genes × TFs); convert to flat edge CSV:

```python
genes = rna.var_names  # or filtered to expressed genes
peaks = atac.var_names[~np.isnan(atac.varm["X_glue"]).any(axis=1)]
tfs   = pd.Index(motif_bed["name"]).intersection(rna.var_names)
if tf_list:
    tfs = tfs.intersection(set(refs.get_tf_list(tf_list)))

gene2tf_rank = scglue.genomics.cis_regulatory_ranking(
    links_df,    # gene2peak: from peak_gene_links_key
    peak2tf,
    genes, peaks, tfs,
    region_lens=atac.var.loc[peaks, "chromEnd"] - atac.var.loc[peaks, "chromStart"],
    random_state=0,
)
# Convert ranking matrix to flat edge list for GRN dataclass
grn_df = (gene2tf_rank
    .stack()
    .reset_index()
    .rename(columns={"level_0": "target_gene", "level_1": "TF", 0: "regulatory_rank"})
)
```

---

#### 3. `multi_peak2gene_glue` — `rna.var["strand"]` column is never produced by `get_gene_annotation()`; `distance_to_tss` silently uses wrong TSS for all minus-strand genes

Verified from the SCGLUE preprocessing tutorial: `scglue.data.get_gene_annotation()` adds only three columns: `chrom`, `chromStart`, `chromEnd`. **No `strand` column is produced.** The plan's code:

```python
has_strand = "strand" in rna.var.columns   # always False — strand never added
if has_strand and rna.var.loc[gene, "strand"] == "-":
    tss = int(rna.var.loc[gene, "chromEnd"])
else:
    tss = int(rna.var.loc[gene, "chromStart"])  # always taken — wrong for - strand genes
```

For - strand genes the TSS is `chromEnd`, not `chromStart`. Roughly half of genes will have `distance_to_tss` computed from the wrong end. The dead `has_strand` code path should be removed and the approximation documented:

```python
# TSS approximated as chromStart (correct for + strand genes).
# get_gene_annotation() does not produce a strand column.
# distance_to_tss is approximate for minus-strand genes (~50% of genes).
tss = int(rna.var.loc[gene, "chromStart"])
peak_mid = (int(atac.var.loc[peak, "chromStart"]) + int(atac.var.loc[peak, "chromEnd"])) // 2
```

If accurate strand-aware distances are required, supplement from the GTF directly (add as a separate optional step or accepted known limitation).

---

### Moderate

#### 4. `multi_grn_glue` — `attr_fn=_motif_attr_fn` added in Pass 4 is incorrect; tutorial uses no `attr_fn`

Pass 4 added `attr_fn=_motif_attr_fn` to ensure motif edges carry `weight`/`sign`. Verified: the SCGLUE tutorial passes **no `attr_fn`** to `window_graph`, and `cis_regulatory_ranking()` (the correct scoring function, issue #2) does not consume edge `weight` or `sign` from `peak2tf` — it uses graph topology and peak lengths only. Remove the custom function:

```python
peak2tf = scglue.genomics.window_graph(
    atac_bed, motif_bed, 0, right_sorted=True,
    # No attr_fn — cis_regulatory_ranking() uses topology only, not edge weights
)
```

---

#### 5. `multi_grn_glue` — `scglue.genomics.regulatory_inference()` high-level function exists and should be evaluated vs. manual `cis_regulatory_ranking` orchestration

Verified from the SCGLUE genomics API: `scglue.genomics.regulatory_inference(features, feature_embeddings, skeleton=skeleton, random_state=0)` exists as a high-level wrapper. It may encapsulate the gene2peak + peak2tf + `cis_regulatory_ranking` pipeline in fewer lines. The plan should evaluate and document which function is used and why — implementers should not encounter this independently and have to choose without guidance. Add a note:

```
# scglue.genomics.regulatory_inference() is a higher-level wrapper that may simplify
# Steps 4–7. Evaluate vs. direct cis_regulatory_ranking() for this use case.
# If regulatory_inference() is used, document its exact signature and inputs.
```

---

## Pass 6 Issues — All Resolved

---

### Critical

#### 1. `multi_grn_glue` — `cis_regulatory_ranking()` first argument must be a NetworkX Graph from `regulatory_inference()`, not a DataFrame; `links_df` raises `TypeError`

The updated plan (Pass 5) passes `links_df` (the cosine-similarity DataFrame produced by `multi_peak2gene_glue`) as the `gene2region` argument to `cis_regulatory_ranking()`. Verified from the SCGLUE API: `cis_regulatory_ranking(gene2region, ...)` expects a NetworkX Graph with edge attributes `score`, `pval`, `qval` — not a DataFrame. Passing a DataFrame raises `TypeError` immediately.

The correct source is `scglue.genomics.regulatory_inference()`, which computes cosine-similarity-based gene↔peak links and returns a NetworkX Graph with the required attributes:

```python
from scglue import genomics

# Collect all feature names and embeddings from both modalities
features   = list(rna.var_names) + list(atac.var_names)
feat_embs  = np.vstack([rna.varm["X_glue"], atac.varm["X_glue"]])

reginf = genomics.regulatory_inference(
    features,
    feat_embs,
    skeleton=guidance_hvg,   # restrict to guidance-graph edges only
    random_state=0,
)

# Filter to high-confidence gene→peak links by q-value
gene2peak = reginf.edge_subgraph(
    [e for e, attr in dict(reginf.edges).items() if attr["qval"] < 0.05]
).copy()

gene2tf_rank = genomics.cis_regulatory_ranking(
    gene2peak,   # NetworkX Graph — NOT links_df DataFrame
    peak2tf,
    genes, peaks, tfs,
    region_lens=atac.var.loc[peaks, "chromEnd"] - atac.var.loc[peaks, "chromStart"],
    random_state=0,
)
```

---

#### 2. `multi_grn_glue` — `peak_bed` passed to `window_graph` must be a `scglue.genomics.Bed` object, not a plain DataFrame; plain DataFrame raises `AttributeError`

The updated plan builds:
```python
atac_bed = atac.var[["chrom", "chromStart", "chromEnd"]].copy()
peak2tf  = scglue.genomics.window_graph(atac_bed, motif_bed, 0, right_sorted=True)
```

Verified from the SCGLUE tutorial: `window_graph` internally calls methods from `scglue.genomics.Bed` (a specialized subclass of `pd.DataFrame`) on the left argument. Passing a plain `pd.DataFrame` raises `AttributeError` on the first Bed-specific method call. The correct construction:

```python
# Filter to peaks with valid (non-NaN) embeddings
peaks    = atac.var_names[~np.isnan(atac.varm["X_glue"]).any(axis=1)]
peak_bed = scglue.genomics.Bed(atac.var.loc[peaks])   # Bed object required

peak2tf = scglue.genomics.window_graph(
    peak_bed,    # scglue.genomics.Bed object — NOT plain DataFrame
    motif_bed,   # also a Bed object from read_bed()
    0,
    right_sorted=True,
)
```

---

#### 3. `multi_grn_glue` — fundamental DAG dependency mismatch: `multi_peak2gene_glue` DataFrame output is incompatible with `cis_regulatory_ranking()`; `multi_grn_glue` must call `regulatory_inference()` directly; DAG must be redesigned

Issues #35 and #36 together reveal an architectural problem: the current DAG has `multi_peak2gene_glue → multi_grn_glue`, implying `multi_grn_glue` consumes the cosine-similarity DataFrame from `multi_peak2gene_glue`. But `cis_regulatory_ranking()` requires a NetworkX Graph from `regulatory_inference()`, which must be called inside `multi_grn_glue` using the raw embeddings (`rna.varm["X_glue"]`, `atac.varm["X_glue"]`) — not from the peak2gene CSV.

This means:

1. **`multi_peak2gene_glue` output is NOT an input to `multi_grn_glue`** — the DAG edge must be removed or replaced with a dotted "informational only" arrow.
2. **`multi_grn_glue` dependency** changes from `multi_peak2gene_glue` to `multi_embed_glue` (needs the GLUE embeddings in `varm["X_glue"]`).
3. **The `peak_gene_links_key` parameter** (currently documented as the way `multi_grn_glue` receives peak2gene links) is unnecessary — remove it from the signature.
4. **`regulatory_inference()` call** must be added to `multi_grn_glue` Step 4 (before `cis_regulatory_ranking`).

Updated DAG edges:
```
multi_preprocess_glue_graph → multi_embed_glue
multi_embed_glue → multi_peak2gene_glue   (cosine similarity output for users)
multi_embed_glue → multi_grn_glue          (GLUE embeddings for regulatory_inference)
multi_preprocess_glue_graph → multi_grn_glue   (guidance graph for regulatory_inference skeleton)
```

`multi_peak2gene_glue` becomes an optional analysis tool branching off `multi_embed_glue`, not a prerequisite of `multi_grn_glue`.

---

### Moderate

#### 4. `multi_grn_glue` — `peak2tf` missing post-`window_graph` edge subgraph filter to restrict edges to expressed TFs

After `window_graph` produces `peak2tf`, the graph contains all TF nodes whose motif hits overlap ATAC peaks — including TFs not detected in RNA. Downstream `cis_regulatory_ranking` ranks all TF nodes in `peak2tf`, including unexpressed TFs that cannot influence transcription and inflate the output table.

Add an edge subgraph filter immediately after `window_graph`:

```python
peak2tf = scglue.genomics.window_graph(peak_bed, motif_bed, 0, right_sorted=True)

# Restrict to TFs that are expressed in RNA
peak2tf = peak2tf.edge_subgraph(
    [e for e in peak2tf.edges if e[1] in set(tfs)]
).copy()
```

This must appear before the `cis_regulatory_ranking` call. Without it, the GRN output will contain TF↔gene edges for TFs with zero RNA expression.

---

#### 5. Refs Store section — intro paragraph still mentions "FASTA files"; stale from before the BED approach pivot in Pass 3

The Refs Store section intro still contains text like: *"…pre-downloaded reference files (genome FASTA, GTF annotation, JASPAR motif files)…"* or equivalent language referencing FASTA genome files. Verified: since Pass 3, the `multi_grn_glue` approach uses pre-computed JASPAR BED files from `window_graph` — no FASTA genome file is needed for motif scanning. The FASTA-referencing refs store entries were supposed to be removed in Pass 3.

Update the intro paragraph and the refs table to remove all genome FASTA entries (`hg38_genome`, `mm10_genome`) and replace any remaining FASTA language with BED-file language. The only genomic reference needed beyond the GTF is the JASPAR motif BED file.

---

## Pass 7 Issues — Open

---

### Moderate

#### 1. `multi_grn_glue` — `genes` passed to `cis_regulatory_ranking()` is `rna.var_names` (all genes); tutorial restricts to HVG genes only; non-HVG genes produce all-zero rankings

The plan at Step 5 defines:
```python
genes = rna.var_names
```

Verified from the SCGLUE regulatory inference tutorial (exact code):
```python
genes = rna.var.query("highly_variable").index
peaks = atac.var.query("highly_variable").index
```

`gene2peak` is filtered from `reginf` which uses `skeleton=guidance_hvg` (HVG subgraph). Therefore `gene2peak` contains edges only between HVG genes and HVG peaks — no non-HVG gene appears in `gene2peak`. When `cis_regulatory_ranking()` receives `genes = rna.var_names` (all genes), it must compute ranks for every gene. For the ~80–90% of genes that are non-HVG, `gene2peak` has zero edges → these genes produce a row of zeros or undefined values in `gene2tf_rank`. This inflates the output matrix with uninformative rows, making the final GRN `grn_df` (after `.stack()`) contain thousands of `(non_HVG_gene, TF, 0.0)` triplets that dilute the real regulatory signal.

Fix:
```python
genes = rna.var_names[rna.var["highly_variable"]]   # match tutorial; only HVG genes
peaks = atac.var_names[~np.isnan(atac.varm["X_glue"]).any(axis=1)]  # already correct
```

---

#### 2. Implementation Order table — `multi_peak2gene_glue` still listed as blocking `multi_grn_glue`; contradicts DAG section and Tool 4 specification

The Implementation Order table (Section near bottom of plan) contains:

```
| 3 | `multi_peak2gene_glue` | `multi_grn_glue` |
```

This says `multi_peak2gene_glue` blocks `multi_grn_glue` — meaning `multi_grn_glue` cannot run until `multi_peak2gene_glue` has run. This directly contradicts:

1. The DAG section explicit note: *"`multi_peak2gene_glue` and `multi_grn_glue` are independent. `multi_grn_glue` does NOT consume `multi_peak2gene_glue` output"*
2. Tool 4 specification: *"`peak_gene_links_key` is NOT a parameter. `multi_grn_glue` does not consume `multi_peak2gene_glue` output"*

Fix the Implementation Order table:
```
| 3 | `multi_peak2gene_glue` | —            |
| 4 | `multi_grn_glue`       | —            |
```

Both tools are optional downstream of `multi_embed_glue` and neither blocks the other.

---

### Minor

#### 3. `multi_grn_glue` — `n_samples` parameter of `cis_regulatory_ranking()` not exposed in tool signature; default silently used

Verified from SCGLUE API: `cis_regulatory_ranking(gene2region, region2tf, genes, regions, tfs, region_lens=None, n_samples=1000, random_state=None)`. The `n_samples=1000` default controls the number of random samples used for enrichment estimation — higher values give more precise p-values at the cost of runtime. On large datasets (>50k peaks, >5k TFs), implementers may need to reduce this for performance or increase it for publication-quality statistics.

The plan calls `cis_regulatory_ranking(..., random_state=0)` without `n_samples`, silently using 1000. Expose it in the tool signature:

```python
def run(
    adata,
    *,
    ...
    reginf_qval: float = 0.05,
    n_ranking_samples: int = 1000,    # ADD — n_samples in cis_regulatory_ranking(); higher = more precise
    output_dir: Path | None = None,
) -> object:
```

Then pass it:
```python
gene2tf_rank = scglue.genomics.cis_regulatory_ranking(
    gene2peak, peak2tf, genes, peaks, tfs,
    region_lens=...,
    n_samples=n_ranking_samples,
    random_state=0,
)
```

---

## Full Issue Tracker

| # | Pass | Severity | Tool | Issue | Status |
|---|---|---|---|---|---|
| 1 | 1 | **Critical** | `multi_preprocess_glue_graph` | `scglue.data.get_peak_annotation()` does not exist → `AttributeError` | ✅ Fixed |
| 2 | 1 | **Critical** | `multi_embed_glue` | `fit_SCGLUE()` does not accept `n_latent`/`n_epochs` directly; must use `init_kws`/`fit_kws` with `latent_dim`/`max_epochs` | ✅ Fixed |
| 3 | 1 | **Critical** | `multi_embed_glue` | `encode_graph()` returns single flat array; split into `rna.varm`/`atac.varm` undocumented | ✅ Fixed |
| 4 | 1 | Moderate | `multi_embed_glue` | `batch_key` not forwarded to `configure_dataset(use_batch=...)` | ✅ Fixed |
| 5 | 1 | Moderate | `multi_embed_glue` | `integration_consistency` in wrong module (`scglue.models.dx`); return is DataFrame not float | ✅ Fixed |
| 6 | 1 | Moderate | `multi_embed_glue` | `use_gpu` not a param of `SCGLUEModel`; GPU control mechanism undocumented | ✅ Fixed |
| 7 | 1 | Moderate | `multi_preprocess_glue_graph` | HVG propagation Step 6 duplicates built-in `propagate_highly_variable=True`; `gene_region`/`promoter_len` not exposed in signature | ✅ Fixed |
| 8 | 1 | Minor | `multi_embed_glue` | `guidance.subgraph()` returns read-only view; needs `.copy()` | ✅ Fixed |
| 9 | 1 | Minor | `multi_preprocess_glue_graph` | `nx.write_graphml_lxml()` requires optional `lxml`; use `nx.write_graphml()` | ✅ Fixed |
| 10 | 1 | Minor | Both | `rna_anchored_guidance_graph` returns `MultiDiGraph`; type implications for `fit_SCGLUE` undocumented | ✅ Fixed |
| 11 | 2 | **Critical** | `multi_preprocess_glue_graph` | `gene_region="promoter_only"` invalid; valid values are `"gene_body"`, `"promoter"`, `"combined"` | ✅ Fixed |
| 12 | 2 | Moderate | `multi_preprocess_glue_graph` + `multi_peak2gene_glue` | `output_dir / "..."` unguarded → `TypeError` when `output_dir=None` | ✅ Fixed |
| 13 | 2 | Moderate | `multi_peak2gene_glue` | Non-HVG features have NaN embeddings; cosine similarity silently corrupts results without NaN guard | ✅ Fixed |
| 14 | 2 | Moderate | `multi_grn_glue` | Motif scanning implementation entirely absent: FASTA genome, scanning library, sequence extraction all unspecified | ✅ Fixed |
| 15 | 2 | Moderate | `multi_embed_glue` | `consistency_df["consistency"]` column name unverified from SCGLUE docs | ✅ Fixed |
| 16 | 2 | Minor | `multi_peak2gene_glue` | `varm["X_glue"][gene]` integer indexing by name not shown; needs name→index dict | ✅ Fixed |
| 17 | 2 | Minor | `multi_embed_glue` | ATAC h5ad write-back path undocumented when `output_dir=None`; pointer not updated | ✅ Fixed |
| 18 | 2 | Minor | `multi_embed_glue` | `configure_dataset(use_layer="counts")` silently fails if `layers["counts"]` absent; add assertion | ✅ Fixed |
| 19 | 3 | **Critical** | `multi_preprocess_glue_graph` + `multi_embed_glue` | Graph lost when `output_dir=None`; no in-memory handoff mechanism; downstream tool cannot load it | ✅ Fixed |
| 20 | 3 | Moderate | `multi_peak2gene_glue` | `distance_to_tss` and `chrom` columns undocumented source; not computed in cosine loop | ✅ Fixed |
| 21 | 3 | Moderate | `multi_grn_glue` | `_scan_peaks_moods()` left as placeholder; SCGLUE-native `window_graph` + JASPAR BED approach simpler, avoids FASTA/MOODS deps | ✅ Fixed |
| 22 | 3 | Moderate | `multi_embed_glue` | `configure_dataset` failure mode comment wrong: raises `ValueError`, not silent fallback | ✅ Fixed |
| 23 | 3 | Minor | `multi_preprocess_glue_graph` | `get_gene_annotation()` missing `gtf_by="gene_name"` → silent all-NaN annotation; no NaN guard | ✅ Fixed |
| 24 | 4 | **Critical** | `multi_grn_glue` | `window_graph()` first arg must be a DataFrame from `scglue.genomics.read_bed()`; passing file path raises `TypeError` | ✅ Fixed |
| 25 | 4 | Moderate | `multi_grn_glue` | `window_graph()` `attr_fn` unspecified; motif edges will lack `weight`/`sign` attributes required for graph scoring | ✅ Fixed |
| 26 | 4 | Moderate | `multi_grn_glue` | TF filtering logic underdocumented; tutorial uses `motif_bed["name"].intersection(rna.var_names)`, not standalone `tf_list` refs entry | ✅ Fixed |
| 27 | 4 | Moderate | `multi_embed_glue` | `consistency_df["consistency"]` defensive column lookup still hedged despite column being confirmed in Pass 3; remove fallback | ✅ Fixed |
| 28 | 4 | Minor | Refs Store | "Existing" table still lists `jaspar_*` for "JASPAR PWM scanning" after switching to BED approach; description misleads implementers | ✅ Fixed |
| 29 | 4 | Minor | `multi_grn_glue` | `compose_multigraph()` return type and edge direction through TF→peak→gene paths undocumented | ✅ Fixed |
| 30 | 5 | **Critical** | `multi_grn_glue` | `window_graph` args reversed: peaks must be left arg, motif BED right; `window_size` is positional; resulting edge direction is peak→TF not TF→peak | ✅ Fixed |
| 31 | 5 | **Critical** | `multi_grn_glue` | Entire scoring algorithm wrong: plan uses `compose_multigraph` + manual traversal; tutorial uses `cis_regulatory_ranking(gene2peak, peak2tf, ...)` with stratified sampling | ✅ Fixed |
| 32 | 5 | **Critical** | `multi_peak2gene_glue` | `rna.var["strand"]` never exists after `get_gene_annotation()`; `distance_to_tss` silently wrong for all - strand genes | ✅ Fixed |
| 33 | 5 | Moderate | `multi_grn_glue` | `attr_fn=_motif_attr_fn` from Pass 4 is unnecessary; tutorial uses no `attr_fn`; `cis_regulatory_ranking()` uses topology only | ✅ Fixed |
| 34 | 5 | Moderate | `multi_grn_glue` | `scglue.genomics.regulatory_inference()` high-level wrapper exists; plan should evaluate and document which API to use | ✅ Fixed |
| 35 | 6 | **Critical** | `multi_grn_glue` | `cis_regulatory_ranking()` first arg must be NetworkX Graph from `regulatory_inference()`, not `links_df` DataFrame; raises `TypeError` | ✅ Fixed |
| 36 | 6 | **Critical** | `multi_grn_glue` | `peak_bed` passed to `window_graph` must be `scglue.genomics.Bed` object, not plain DataFrame; raises `AttributeError` | ✅ Fixed |
| 37 | 6 | **Critical** | `multi_grn_glue` + DAG | Fundamental DAG mismatch: `multi_peak2gene_glue` DataFrame output incompatible with `cis_regulatory_ranking`; `multi_grn_glue` must call `regulatory_inference()` directly using `varm["X_glue"]`; DAG `multi_peak2gene_glue → multi_grn_glue` edge must be removed | ✅ Fixed |
| 38 | 6 | Moderate | `multi_grn_glue` | `peak2tf` missing edge subgraph filter `peak2tf.edge_subgraph(e for e in peak2tf.edges if e[1] in tfs)` after `window_graph`; unexpressed TFs inflate GRN output | ✅ Fixed |
| 39 | 6 | Moderate | Refs Store | Intro paragraph still mentions "FASTA files"; stale from before the BED approach pivot in Pass 3; `hg38_genome`/`mm10_genome` entries still present | ✅ Fixed |
| 40 | 7 | Moderate | `multi_grn_glue` | `genes = rna.var_names` (all genes) passed to `cis_regulatory_ranking()`; tutorial uses HVG genes only; non-HVG genes have no `gene2peak` edges and produce all-zero ranking rows, inflating GRN output | ⚠️ Open |
| 41 | 7 | Moderate | Implementation Order table | `multi_peak2gene_glue` listed as blocking `multi_grn_glue`; contradicts DAG section and Tool 4 note that both are independent branches of `multi_embed_glue` | ⚠️ Open |
| 42 | 7 | Minor | `multi_grn_glue` | `n_samples` parameter of `cis_regulatory_ranking()` (default 1000) not exposed in tool signature; users cannot tune sampling precision for large datasets | ⚠️ Open |
