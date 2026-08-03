---
type: tool
id: rna_grn_decoupler
modality: rna
stage: grn_inference
backend: backend/tools/rna/grn/decoupler.py
label: TF Activity Scoring (decoupler + CollecTRI)
default: true
params:
  network: collectri
  organism: human
  min_n: 5
---

Estimates TF activity scores across cells using decoupler-py's ULM (Univariate Linear Model) with a curated prior knowledge network.

Key parameters:
- `network` (default "collectri")
- `organism` (default "human")
- `min_n` (default 5)

Does NOT infer new TF–gene edges. Instead, scores how active each known TF is in each cell given its curated target genes (CollecTRI / DoRothEA).

**Outputs stored in adata:**
- `adata.obsm["ulm_estimate"]`: TF activity matrix (cells × TFs)
- `adata.obsm["ulm_pvals"]`: associated p-values

**When to use:**
- Default choice for RNA-only GRN analysis
- When TF activity per cell type / cluster is the goal
- Fast (minutes); no ATAC or external database files required

**Params:**
- `network`: "collectri" (default, ~1000 human TFs, signed) or "dorothea" (A–C confidence)
- `organism`: "human" or "mouse"
- `min_n`: minimum targets per TF to be scored (default 5)

Package: [[packages/decoupler]]
Method: [[methods/prior_knowledge_grn]] [rna]
