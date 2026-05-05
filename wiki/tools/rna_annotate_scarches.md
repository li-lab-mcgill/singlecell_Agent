---
type: tool
id: rna_annotate_scarches
stage: annotate
modality: rna
backend: backend/tools/rna/annotate/scarches.py
---

Annotates cells by mapping a query dataset onto a pretrained scVI/scANVI reference model using scArches (surgery-based transfer learning). The query model is fine-tuned on the reference while freezing reference weights.

Key parameters:
- `reference_model_path` (required): path to a pretrained scVI or scANVI model directory
- `max_epochs` (default 100): fine-tuning epochs for the surgery step
- `batch_key` (default None): batch key in the query dataset; must match the reference model's batch structure if specified

scArches allows mapping new data onto existing atlases without retraining the reference. This is useful for adding new samples to an existing annotated reference.

Output:
- `adata.obsm["X_scarches"]`: query embedding in reference latent space
- `adata.obs["scarches_cell_type"]`: transferred labels via KNN in reference latent space

Package: [[packages/scvi_tools]]
Method: [[methods/reference_based_annotation]]
