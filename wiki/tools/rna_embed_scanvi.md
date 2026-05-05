---
type: tool
id: rna_embed_scanvi
stage: embed
modality: rna
backend: backend/tools/rna/embed/scanvi.py
---

Trains a scANVI model (semi-supervised scVI) using partial cell type labels as supervision. Produces a label-aware latent embedding that improves both batch correction and cluster separation when some cells have known labels.

Key parameters:
- `labels_key` (default "cell_type"): `adata.obs` column with known cell type labels; cells without labels should have value `"Unknown"`
- `n_latent` (default 30): latent space dimensionality
- `n_epochs_unsupervised` (default 200): initial unsupervised pre-training epochs (trains an scVI model first)
- `n_epochs_semisupervised` (default 100): additional semi-supervised fine-tuning epochs
- `batch_key` (default None): batch correction key; same as scVI

scANVI is a two-stage model: it first trains an unsupervised scVI model, then fine-tunes using the known labels. Only cells with known labels contribute to the supervised loss.

Use when: a subset of cells have known labels (e.g., from a pilot study or sorted populations), and you want to leverage that information to improve the embedding.

Stores embedding in `adata.obsm["X_scanvi"]`.

Package: [[packages/scvi_tools]]
Method: [[methods/deep_generative_embedding]]
