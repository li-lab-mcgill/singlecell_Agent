---
type: method
id: highly_variable_peaks
label: Highly Variable Peak Selection
---

Highly variable peak selection retains ATAC peaks with the most variability across cells, reducing dimensionality and focusing the embedding on informative regulatory regions.

For ATAC data, peak accessibility is binary or near-binary, making the "variance" criterion different from RNA. Peaks that are accessible in nearly all cells (constitutive) or nearly no cells (rare noise) contribute little to cell-type discrimination.

Selection criteria:
- **Top-N by mean accessibility**: select peaks accessible in 5–50% of cells (avoids constitutive and rare peaks)
- **Top-N by variance-to-mean ratio**: similar to RNA dispersion approach; implemented in SnapATAC2

In SnapATAC2, feature selection is done implicitly: `snap.pp.select_features(adata, n_top_features=50000)` marks the top variable peaks for downstream spectral embedding.

Typical target: 50,000 peaks for human genomes; fewer for smaller/simpler organisms.

Edges:
- [[tools/atac_feature_selection_peaks]] implements
