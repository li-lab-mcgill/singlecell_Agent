---
type: tool
id: rna_grn_pyscenic
modality: rna
stage: grn_inference
backend: backend/tools/rna/grn/pyscenic.py
label: Full GRN with Regulons (pySCENIC)
default: false
params:
  n_jobs: 4
  seed: 42
  rank_threshold: 1500
  auc_threshold: 0.05
  nes_threshold: 3.0
requires_resources:
  - resource: pyscenic_databases
    params:
      - tf_list_path
      - cistarget_db_paths
      - motif_annotations_path
    download_utility: backend.tools.rna.grn.download_databases
    note: >
      Large files (15–47 GB total). Must be downloaded before the pipeline runs.
      Ask the user for file paths or whether they have already downloaded the databases.
      If not, show the download instructions before including this tool in the plan.
---

Full pySCENIC pipeline: GRNBoost2 co-expression inference + cisTarget motif pruning → validated regulons.

Key parameters:
- `tf_list_path` (required)
- `cistarget_db_paths` (required)
- `motif_annotations_path` (required)
- `n_jobs` (default 4)
- `seed` (default 42)
- `rank_threshold` (default 1500)
- `auc_threshold` (default 0.05)
- `nes_threshold` (default 3.0)

**Two stages:**
1. **GRNBoost2**: scores all TF→gene co-expression pairs (weighted adjacency matrix)
2. **cisTarget (ctx)**: retains only TF→gene edges where the TF's binding motif is enriched in the gene's cis-regulatory region → produces regulons

**Outputs stored in adata:**
- `adata.uns["pyscenic_regulons"]`: dict of `{TF_name: [target_genes]}`

**Required external files (large, downloaded once):**
- `tf_list_path`: TF symbol list (e.g. `allTFs_hg38.txt`, ~1800 human TFs) — from pySCENIC resources
- `cistarget_db_paths`: one path or a list of `.feather` cisTarget ranking databases. Using two databases together (e.g. `500bp` + `10kb`, or `refseq` + `screen`) improves regulon coverage. All must match the same genome assembly. Examples:
  - `hg38__refseq-r80__500bp_up_and_100bp_down_tss.mc9nr.feather` (tight promoter)
  - `hg38__refseq-r80__10kb_up_and_down_tss.mc9nr.feather` (proximal cis-regulatory)
  - `hg38__SCREEN__v10_clust.genes_vs_motifs.rankings.feather` (ENCODE cCREs, distal enhancers)
  - Mouse equivalents use `mm10__` prefix
- `motif_annotations_path`: motif-to-TF annotation TSV — must match the motif collection of the databases:
  - `motifs-v9-nr.hgnc-m0.001-o0.0.tbl` (for human refseq v9 databases)
  - `motifs-v9-nr.mgi-m0.001-o0.0.tbl` (for mouse)

See [[resources/pyscenic_databases]] for download links.

**When to use:**
- When the user needs full regulon structure with motif validation (publication-quality)
- Slower than GRNBoost2 alone (hours on large datasets); requires ~20 GB of database files

**Params:**
- `rank_threshold`: genes ranked above this in the cisTarget DB are considered (default 1500)
- `auc_threshold`: AUC cutoff for regulon inclusion (default 0.05)
- `nes_threshold`: normalized enrichment score cutoff (default 3.0)

Package: [[packages/pyscenic]]
Method: [[methods/coexpression_grn]] [rna]
