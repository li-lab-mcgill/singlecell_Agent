---
type: tool
id: atac_peak_calling_macs3
stage: peak_calling
modality: atac
backend: backend/tools/atac/peak_calling/macs3.py
---

Calls peaks using MACS3 with per-cluster pseudo-bulk aggregation. Generates a consensus peak set across all clusters.

Key parameters:
- `group_key` (default None)
- `q_value` (default 0.05)

Workflow:
1. For each cluster: extract barcodes, filter fragment file → run MACS3 `--format BEDPE --nomodel --shift -100 --extsize 200`
2. Merge all per-cluster peaks into a consensus peak set using bedtools merge
3. Re-quantify consensus peaks across all cells → updates `adata` with new peak matrix

Output: new `adata.X` with consensus peak counts, `adata.var` updated with consensus peak coordinates.

Package: [[packages/macs3]]
Method: [[methods/macs_peak_calling]]
