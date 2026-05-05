---
type: package
id: muon
version: ">=0.1.5"
citation: Bredikhin et al. 2022 Genome Biology
---

muon is a Python framework for multi-modal single-cell data. It introduces `MuData`, a container that holds multiple `AnnData` objects (one per modality) with shared observations.

Install: `pip install muon`

The `MuData` object stores modalities under `mdata.mod["rna"]`, `mdata.mod["atac"]`, etc. Global cell-level metadata is in `mdata.obs`; modality-specific metadata is in each `mdata.mod[key].obs`.

Key capabilities:

- **MOFA+**: `muon.tl.mofa()` — multi-omics factor analysis; decomposes variation across modalities into shared latent factors stored in `mdata.obsm["X_mofa"]`
- **WNN (Weighted Nearest Neighbors)**: `muon.pp.neighbors()` with `use_rep` per modality — computes modality-weighted neighbor graph for joint clustering and UMAP
- **Multi-modal UMAP**: `muon.tl.umap()` — UMAP on WNN graph
- **Preprocessing**: `muon.pp.filter_obs()`, `muon.pp.intersect_obs()` — align cells across modalities

For 10x Multiome data (paired RNA+ATAC), load with `muon.read_10x_h5()` which creates a `MuData` with `rna` and `atac` modalities pre-aligned.

MOFA+ requires the `mofapy2` package as backend. WNN integration requires that each modality has its own neighbor graph computed first. [Bredikhin et al. 2022]
