---
type: package
id: scvi_tools
version: ">=1.0"
citation: Lopez et al. 2018 Nature Methods (scVI); Xu et al. 2021 Molecular Systems Biology (scANVI); Ashuach et al. 2022 Nature Methods (MultiVI)
---

scvi-tools is a deep probabilistic framework for single-cell omics built on PyTorch Lightning. It provides variational autoencoder models that learn batch-corrected latent representations while preserving biological variation.

Install: `pip install scvi-tools`

Key models used in this wiki:
- `scvi.model.SCVI` — unsupervised RNA embedding with optional batch correction via `batch_key`
- `scvi.model.SCANVI` — semi-supervised embedding using partial cell type labels
- `scvi.model.MULTIVI` — joint RNA+ATAC embedding for multiome data
- `scvi.model.PEAKVI` — ATAC-only variational embedding

All models require `setup_anndata()` before instantiation. Raw counts must be in `adata.layers["counts"]`. Training uses Lightning — GPU acceleration available via `accelerator="gpu"`.

scVI inherently handles batch correction when `batch_key` is set — no separate integration step needed. This is why `rna_embed_scvi` appears under both embed and batch_integration stages.
