---
type: package
id: scib_metrics
version: ">=0.4"
citation: Luecken et al. 2022 Nature Methods
---

scib-metrics is a Python reimplementation of the scIB (single-cell integration benchmarking) metric suite. It provides standardized metrics for evaluating batch correction quality and biological conservation.

Install: `pip install scib-metrics`

Key metrics:

**Batch correction metrics** (higher = better batch mixing):
- `scib_metrics.ilisi_graph()` — iLISI: integration local inverse Simpson's Index; measures batch mixing in the neighborhood graph
- `scib_metrics.kbet()` — kBET: k-nearest neighbor batch effect test; acceptance rate of batch label shuffling test
- `scib_metrics.graph_connectivity()` — fraction of cells connected across batches for each cell type

**Biological conservation metrics** (higher = better preservation of biology):
- `scib_metrics.clisi_graph()` — cLISI: cell type local inverse Simpson's Index; measures cell type purity in neighborhoods
- `scib_metrics.nmi()` — NMI between Leiden clusters on integrated embedding and ground-truth labels
- `scib_metrics.ari()` — ARI between Leiden clusters and ground-truth labels
- `scib_metrics.silhouette_label()` — silhouette score using cell type labels
- `scib_metrics.isolated_label_asw()` — average silhouette width for isolated cell types

**Overall score**: The scIB paper computes a composite score as the mean of batch correction and bio conservation sub-scores. Equal weighting is typical but weights can be adjusted. [Luecken et al. 2022]

All metrics accept an `AnnData` object plus `batch_key` and `label_key` arguments. The graph-based metrics (iLISI, kBET, cLISI) operate on `adata.obsp["connectivities"]` — run `sc.pp.neighbors()` on the integrated embedding first.
