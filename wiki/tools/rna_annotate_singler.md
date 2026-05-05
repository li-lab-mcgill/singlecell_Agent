---
type: tool
id: rna_annotate_singler
stage: annotate
modality: rna
backend: backend/tools/rna/annotate/singler.py
---

Annotates cells using SingleR, a correlation-based reference annotation method. Computes Spearman correlations between each query cell and each reference cell type's expression profile, then assigns the best-correlated label.

Key parameters:
- `reference` (default "HumanPrimaryCellAtlasData"): Bioconductor reference dataset; options include `"HumanPrimaryCellAtlasData"`, `"BlueprintEncodeData"`, `"MonacoImmuneData"`, `"ImmGenData"` (mouse)
- `fine_tune` (default True): refine low-confidence calls by re-scoring against top candidate labels
- `cluster_key` (default None): if set, scores per cluster rather than per cell (faster, less noisy)

Requires R and the `SingleR` Bioconductor package via `rpy2`. Falls back to CellTypist if R is unavailable.

Output: `adata.obs["singler_cell_type"]` and `adata.obs["singler_score"]`.

Package: [[packages/sklearn]] (rpy2-based R bridge; requires R SingleR)
Method: [[methods/reference_based_annotation]]
