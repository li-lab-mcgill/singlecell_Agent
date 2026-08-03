---
type: method
id: batch_metrics
label: Batch Correction Quality Metrics
---

Batch metrics evaluate two complementary properties of an integration: how well batches are mixed (batch correction) and how well biological structure is preserved (bio conservation). A good integration maximizes both.

**Batch correction metrics** (higher = better batch mixing):
- **iLISI**: integration Local Inverse Simpson's Index; measures diversity of batches in each cell's neighborhood; ranges from 1 (no mixing) to n_batches (perfect mixing)
- **kBET**: k-nearest neighbor Batch Effect Test; acceptance rate of a batch label distribution test in local neighborhoods; higher = better mixing
- **Graph connectivity**: fraction of cells per cell type that are connected across batches in the KNN graph

**Bio conservation metrics** (higher = better biological preservation):
- **cLISI**: cell type Local Inverse Simpson's Index; measures cell type purity in neighborhoods; should be high after good integration
- **NMI/ARI on clusters**: Leiden clusters on integrated embedding vs. ground-truth labels
- **Silhouette (label)**: silhouette score using cell type as label; measures cell type separation in integrated space
- **Isolated label ASW**: average silhouette width for cell types present in only one batch (most vulnerable to over-correction)

**Composite scIB score**: mean of batch correction sub-score and bio conservation sub-score. Standard for comparing integration methods.

Computed using scib-metrics package.

Edges:
- [[tools/eval_ilisi_clisi]] implements
- [[tools/eval_kbet]] implements
