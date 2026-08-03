---
type: tool
id: rna_grn_grnboost2
modality: rna
stage: grn_inference
backend: backend/tools/rna/grn/grnboost2.py
label: Co-expression GRN Inference (GRNBoost2)
default: false
params:
  n_jobs: 4
  seed: 42
---

Infers TF → gene importance scores from expression co-variation using GRNBoost2 (gradient-boosted trees). Produces a weighted adjacency matrix: each row is a (TF, target, importance) triple.

Key parameters:
- `tf_list_path` (default None)
- `n_jobs` (default 4)
- `seed` (default 42)

GRNBoost2 is the co-expression engine inside pySCENIC, but runs here as a standalone step — no motif databases required. Use this when:
- You want a co-expression network quickly without cisTarget databases
- You plan to apply a custom pruning step downstream
- You want to feed the adjacency matrix into pySCENIC ctx separately

**Outputs stored in adata:**
- `adata.uns["grnboost2_adjacencies"]`: list of `{TF, target, importance}` dicts

**Limitations:**
- No motif validation — many edges will be indirect co-regulation, not direct TF binding
- For validated regulons, use `rna_grn_pyscenic` (runs GRNBoost2 + cisTarget ctx)

**Params:**
- `tf_list_path`: path to TF symbol list file; if None, all genes used (slow, not recommended)
- `n_jobs`: parallel workers (default 4)
- `seed`: random seed (default 42)

Package: [[packages/pyscenic]]
Method: [[methods/coexpression_grn]] [rna]
