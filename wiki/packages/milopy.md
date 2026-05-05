---
type: package
id: milopy
version: ">=0.1"
citation: Dann et al. 2022 Nature Biotechnology
---

Milo (Python implementation: milopy) tests for differential cell abundance between conditions using neighborhoods on a k-nearest neighbor graph. Unlike clustering-based DA, Milo operates at the neighborhood level, enabling detection of continuous compositional shifts that cross cluster boundaries.

Install: `pip install milopy`

Milo workflow:
1. `milo.make_nhoods(adata)` — samples representative cells as neighborhood index cells
2. `milo.count_nhoods(adata, sample_col="sample")` — counts cells per neighborhood per sample
3. `milo.DA_nhoods(adata, design="~ condition")` — runs quasi-binomial GLM per neighborhood; returns log fold change and FDR-corrected p-values
4. `milo.build_nhood_graph(adata)` — builds spatial graph of neighborhoods for visualization
5. `milo.plot_nhood_graph(adata)` — plots DA results on UMAP with neighborhood nodes colored by log fold change

Key parameters in `make_nhoods()`:
- `prop` (default 0.1): fraction of cells to use as index cells; lower = fewer neighborhoods, faster but lower resolution
- `k` (default 30): number of neighbors per cell; inherited from the KNN graph

Output: `adata.uns["nhood_adata"]` — an AnnData of neighborhoods with DA test results in `.obs["logFC"]`, `.obs["PValue"]`, `.obs["SpatialFDR"]`.

Milo requires biological replicates (≥3 samples per condition) for valid DA testing. Single-sample comparisons will fail the GLM fitting. [Dann et al. 2022]
