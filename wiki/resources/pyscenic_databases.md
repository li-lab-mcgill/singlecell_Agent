---
type: resource
id: pyscenic_databases
label: pySCENIC cisTarget Databases
download_utility: backend.tools.rna.grn.download_databases
presets:
  human_minimal:
    aliases: [hg38_refseq_10kb, hg38_motifs, hg38_tfs]
    size_gb: 15
    description: Human hg38 — single database (±10kb TSS). Minimum to run pySCENIC ctx.
    resolves:
      tf_list_path: hg38_tfs
      cistarget_db_paths: [hg38_refseq_10kb]
      motif_annotations_path: hg38_motifs
  human:
    aliases: [hg38_refseq_500bp, hg38_refseq_10kb, hg38_motifs, hg38_tfs]
    size_gb: 31
    description: Human hg38 — two databases (500bp + 10kb). Standard, better regulon coverage.
    resolves:
      tf_list_path: hg38_tfs
      cistarget_db_paths: [hg38_refseq_500bp, hg38_refseq_10kb]
      motif_annotations_path: hg38_motifs
  human_with_screen:
    aliases: [hg38_refseq_500bp, hg38_refseq_10kb, hg38_screen, hg38_motifs, hg38_tfs]
    size_gb: 48
    description: Human hg38 — refseq + SCREEN cCREs. Best coverage including distal enhancers.
    resolves:
      tf_list_path: hg38_tfs
      cistarget_db_paths: [hg38_refseq_500bp, hg38_refseq_10kb, hg38_screen]
      motif_annotations_path: hg38_motifs
  human_hg19:
    aliases: [hg19_refseq_500bp, hg19_refseq_10kb, hg38_motifs, hg38_tfs]
    size_gb: 31
    description: Human hg19 — two databases (standard)
    resolves:
      tf_list_path: hg38_tfs
      cistarget_db_paths: [hg19_refseq_500bp, hg19_refseq_10kb]
      motif_annotations_path: hg38_motifs
  mouse_minimal:
    aliases: [mm10_refseq_10kb, mm10_motifs, mm10_tfs]
    size_gb: 13
    description: Mouse mm10 — single database (±10kb TSS). Minimum to run pySCENIC ctx.
    resolves:
      tf_list_path: mm10_tfs
      cistarget_db_paths: [mm10_refseq_10kb]
      motif_annotations_path: mm10_motifs
  mouse:
    aliases: [mm10_refseq_500bp, mm10_refseq_10kb, mm10_motifs, mm10_tfs]
    size_gb: 26
    description: Mouse mm10 — two databases (standard)
    resolves:
      tf_list_path: mm10_tfs
      cistarget_db_paths: [mm10_refseq_500bp, mm10_refseq_10kb]
      motif_annotations_path: mm10_motifs
---

External database files required for the cisTarget motif pruning step in `rna_grn_pyscenic`.
All files are hosted at https://resources.aertslab.org/cistarget/

## Available presets

| Preset | Size | Description |
|--------|------|-------------|
| `human_minimal` | **~15 GB** | Human hg38 — single database (10kb). Minimum to run pySCENIC. |
| `human` | ~31 GB | Human hg38 — two databases (500bp + 10kb). Standard, better coverage. |
| `human_with_screen` | ~48 GB | Human hg38 — refseq + ENCODE SCREEN cCREs (distal enhancers). |
| `human_hg19` | ~31 GB | Human hg19 — two databases. |
| `mouse_minimal` | **~13 GB** | Mouse mm10 — single database (10kb). Minimum to run pySCENIC. |
| `mouse` | ~26 GB | Mouse mm10 — two databases (standard). |

**Note:** If you want zero downloads, use `rna_grn_grnboost2` instead — it runs co-expression inference with no external files required.

## Database files

### cisTarget ranking databases (.feather)

| Alias | File | Size | Notes |
|-------|------|------|-------|
| `hg38_refseq_10kb` | `hg38__refseq-r80__10kb_up_and_down_tss.mc9nr.feather` | 15 GB | Standard default — ±10kb TSS |
| `hg38_refseq_500bp` | `hg38__refseq-r80__500bp_up_and_100bp_down_tss.mc9nr.feather` | 15 GB | Tight promoter window |
| `hg38_screen` | `hg38__SCREEN__v10_clust.genes_vs_motifs.rankings.feather` | 17 GB | ENCODE cCREs (distal enhancers) |
| `hg19_refseq_10kb` | `hg19__refseq-r80__10kb_up_and_down_tss.mc9nr.feather` | 15 GB | hg19 |
| `hg19_refseq_500bp` | `hg19__refseq-r80__500bp_up_and_100bp_down_tss.mc9nr.feather` | 15 GB | hg19 tight |
| `mm10_refseq_10kb` | `mm10__refseq-r80__10kb_up_and_down_tss.mc9nr.feather` | 13 GB | Mouse |
| `mm10_refseq_500bp` | `mm10__refseq-r80__500bp_up_and_100bp_down_tss.mc9nr.feather` | 13 GB | Mouse tight |

### Motif annotations (.tbl) and TF lists (.txt)

| Alias | File | Organism |
|-------|------|----------|
| `hg38_motifs` | `motifs-v9-nr.hgnc-m0.001-o0.0.tbl` | Human |
| `mm10_motifs` | `motifs-v9-nr.mgi-m0.001-o0.0.tbl` | Mouse |
| `hg38_tfs` | `allTFs_hg38.txt` | Human (~1800 TFs) |
| `mm10_tfs` | `allTFs_mm.txt` | Mouse (~1600 TFs) |

## SCENIC+ compatibility

These same database files are used by **SCENIC+** (`multi_grn_pycistarget`, `multi_grn_scenicplus`). No additional download is needed if you have already downloaded databases for `rna_grn_pyscenic`.

**Important — `annotation_version` must match your actual files:**
- Files listed in this resource use `mc9nr` naming (e.g. `hg38__refseq-r80__10kb_up_and_down_tss.mc9nr.feather`). These are v9-era databases. Set `annotation_version='v9'` (the default) when using these files with `multi_grn_pycistarget`.
- If you have downloaded separate `v10nr_clust` feather files (e.g. `hg38_10kbp_up_10kbp_down_full_tx_v10_clust.genes_vs_motifs.rankings.feather`), set `annotation_version='v10nr_clust'` instead.
- **Setting the wrong version causes a silent annotation mismatch** — TF names will be looked up from the wrong version's annotation table, producing unreliable motif enrichment results.
