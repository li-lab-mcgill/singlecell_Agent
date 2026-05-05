---
type: package
id: snapatac2
version: ">=2.5"
citation: Zhang et al. 2024 Nature Methods
---

SnapATAC2 is a scalable Python toolkit for single-cell ATAC-seq analysis. It uses an efficient fragment-based data model and bit-array representations to handle millions of cells without loading full count matrices into memory.

Install: `pip install snapatac2`

SnapATAC2 uses its own `AnnData`-compatible object but integrates with standard scanpy workflows. Key stages:

- **Fragment ingestion**: `snap.pp.import_data()` — reads fragment files directly
- **QC**: `snap.metrics.tsse()` — TSS enrichment score; `snap.pl.tsse()` for visual QC
- **Feature matrix**: `snap.pp.add_tile_matrix()` (500 bp bins) or `snap.pp.make_peak_matrix()` (peak-based)
- **Dimensionality reduction**: `snap.tl.spectral()` — spectral embedding on TF-IDF transformed tile matrix; equivalent to LSI in other tools
- **Batch correction**: `snap.tl.harmony()` — harmony integration on spectral embedding
- **Clustering**: `snap.tl.leiden()` — Leiden clustering on snap neighbor graph
- **Peak calling**: `snap.tl.macs3()` — calls MACS3 per cluster; `snap.tl.merge_peaks()` — merges into consensus peak set
- **Differential accessibility**: `snap.tl.diff_test()` — logistic regression-based DA testing

The spectral embedding is stored in `adata.obsm["X_spectral"]`. After batch correction via harmony, the corrected embedding is in `adata.obsm["X_spectral_harmony"]`.

Key difference from ArchR: SnapATAC2 is pure Python and integrates directly with the scanpy/AnnData ecosystem. For large datasets (>500k cells), SnapATAC2 outperforms all other ATAC tools in memory efficiency. [Zhang et al. 2024]
