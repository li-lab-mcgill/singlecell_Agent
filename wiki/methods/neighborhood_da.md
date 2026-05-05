---
type: method
id: neighborhood_da
label: Neighborhood-based Differential Abundance (Milo)
---

Milo tests for differential cell abundance using neighborhoods in the KNN graph rather than discrete clusters. It computes a quasi-binomial GLM for each neighborhood, testing whether the proportion of cells from each condition differs significantly from expectation.

This approach captures continuous compositional shifts that span multiple clusters or that do not align with cluster boundaries — common in disease versus healthy comparisons where affected states are transitional.

Workflow:
1. `milo.make_nhoods(adata, prop=0.1)` — sample index cells
2. `milo.count_nhoods(adata, sample_col="sample")` — count cells per neighborhood per sample
3. `milo.DA_nhoods(adata, design="~ condition")` — quasi-binomial GLM
4. `milo.build_nhood_graph(adata)` — spatial graph for visualization
5. `milo.plot_nhood_graph(adata)` — color UMAP by neighborhood log fold change

Statistical model: quasi-binomial GLM handles overdispersion in count data. The spatial FDR correction accounts for the fact that overlapping neighborhoods are not independent.

Requirements: ≥3 biological replicates per condition. The `design` formula can include covariates (e.g., `"~ condition + age"`).

Edges:
- [[tools/rna_da_milo]] implements
- [[tools/atac_da_milo]] implements
