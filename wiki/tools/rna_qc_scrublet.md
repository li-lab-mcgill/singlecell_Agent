---
type: tool
id: rna_qc_scrublet
stage: qc
modality: rna
backend: backend/tools/rna/qc/scrublet.py
---

Detects and removes predicted doublets using Scrublet. Simulates artificial doublets by combining pairs of real cell profiles, then scores each cell by similarity to the simulated doublets.

Key parameters:
- `expected_doublet_rate` (default 0.06)

Stores results in `adata.obs["doublet_score"]` (float) and `adata.obs["predicted_doublet"]` (bool).

Must be run per sample/batch if dataset contains multiple batches. Running on pooled data underestimates the doublet rate.

Package: [[packages/scvi_tools]] (scvi-tools includes scrublet-compatible doublet detection via `sc.pp.scrublet`)
Method: [[methods/doublet_detection]]
