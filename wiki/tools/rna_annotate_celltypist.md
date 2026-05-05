---
type: tool
id: rna_annotate_celltypist
stage: annotate
modality: rna
backend: backend/tools/rna/annotate/celltypist.py
---

Annotates cells using CellTypist pretrained logistic regression models. Downloads the specified model (cached after first use) and predicts cell type labels per cell.

Key parameters:
- `model` (default "Immune_All_Low.pkl"): pretrained model name; options include `"Immune_All_Low.pkl"` (fine-grained immune), `"Immune_All_High.pkl"` (coarse immune), `"Pan_Fetal_Human.pkl"` (fetal tissues)
- `majority_voting` (default True): smooth predictions by cluster membership; recommended
- `cluster_key` (default "leiden_clusters"): cluster label column for majority voting; must be present in `adata.obs`
- `min_prob` (default 0.5): flag cells with confidence below this threshold

Outputs:
- `adata.obs["celltypist_cell_type"]`: per-cell predicted label
- `adata.obs["celltypist_conf_score"]`: confidence score (0–1)
- `adata.obs["majority_voting"]`: cluster-smoothed label (if majority_voting=True)

Requires log-normalized expression (not raw counts). Run after `rna_normalize_log1p`.

Package: [[packages/celltypist]]
Method: [[methods/reference_based_annotation]]
