---
type: method
id: doublet_detection
label: Doublet Detection
---

Doublet detection identifies barcodes that represent two cells captured in the same droplet. Doublets appear as cells with unusually high transcript counts or as artificial intermediate states between two cell types.

The Scrublet algorithm simulates doublets by combining pairs of real cell profiles, then scores each cell by its similarity to simulated doublets. Cells above a threshold (typically 0.25) are flagged as predicted doublets.

Key considerations:
- Run Scrublet per sample/batch, not on the pooled dataset — doublet rates vary by capture density
- Doublet rate is approximately 1% per 1000 cells captured (10x Genomics spec)
- Cells flagged as doublets should be inspected before removal — some intermediate states (e.g., macrophages engulfing debris) may score high

After flagging, cells are stored with `adata.obs["predicted_doublet"]` (bool) and `adata.obs["doublet_score"]` (float). Filtering removes `predicted_doublet == True`.

Edges:
- [[tools/rna_qc_scrublet]] implements
