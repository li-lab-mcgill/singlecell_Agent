---
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
---

Completes the pySCENIC pipeline by running AUCell (stage 3) on the regulons produced by `rna_grn_pyscenic`. Scores each cell for TF regulon activity by computing the enrichment of regulon target genes in the cell's top-ranked expressed genes.

This is the missing third stage of pySCENIC (`grn → ctx → aucell`). If you ran `rna_grn_pyscenic` you likely want to run this next.

## AUCell algorithm

For each cell and each regulon:
1. Rank all genes by expression (highest expression = lowest rank)
2. Count how many regulon target genes fall in the top `auc_threshold × n_genes` positions
3. Normalize to get AUC ∈ [0, 1]; high AUC = regulon active in that cell

Uses `pyscenic.aucell.aucell()` and `create_rankings()` when available; falls back to manual ranking via `scipy.stats.rankdata` otherwise.

## Outputs stored in adata

| Key | Type | Description |
|-----|------|-------------|
| `adata.obsm["X_pyscenic_auc"]` | ndarray (cells × TFs) | Regulon activity matrix |
| `adata.uns["pyscenic_auc_tf_names"]` | list | TF regulon name index for obsm columns |

**obsm stores numpy arrays** — column names are saved separately in `adata.uns["pyscenic_auc_tf_names"]` for reconstruction.

**Params:**
- `regulons_key`: adata.uns key for the `{TF: [genes]}` regulon dict (default `'pyscenic_regulons'`)
- `auc_threshold`: fraction of top-ranked genes used for AUC (default 0.05)
- `n_cpu`: parallel workers (default 4)
- `seed`: random seed (default 42)

Package: [[packages/pyscenic]]
Method: [[methods/coexpression_grn]]
