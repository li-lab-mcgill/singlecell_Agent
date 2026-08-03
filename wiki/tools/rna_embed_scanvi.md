---
type: tool
id: rna_embed_scanvi
stage: embed
modality: rna
backend: backend/tools/rna/embed/scanvi.py
---

Trains a scANVI model (semi-supervised scVI) using partial cell type labels as supervision. Produces a label-aware latent embedding that improves both batch correction and cluster separation when some cells have known labels.

Key parameters:
- `label_key` (required)
- `batch_key` (default None)
- `n_latent` (default 30)
- `n_epochs` (default None)
- `accelerator` (default "auto")
- `devices` (default "auto")
- `precision` (default None)

scANVI is a two-stage model: it first trains an unsupervised scVI model, then fine-tunes using the known labels. Only cells with known labels contribute to the supervised loss.

Use when: a subset of cells have known labels (e.g., from a pilot study or sorted populations), and you want to leverage that information to improve the embedding.

Stores embedding in `adata.obsm["X_scanvi"]`.

Package: [[packages/scvi_tools]]
Method: [[methods/deep_generative_embedding]]
