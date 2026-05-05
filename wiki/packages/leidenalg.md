---
type: package
id: leidenalg
version: ">=0.9"
citation: Traag et al. 2019 Scientific Reports
---

leidenalg implements the Leiden community detection algorithm, which improves on Louvain by guaranteeing well-connected communities. Used via scanpy's `sc.tl.leiden()` wrapper.

Install: `pip install leidenalg`

Leiden is the preferred clustering algorithm over Louvain for single-cell data. It produces more consistent partitions across runs and is actively maintained. Use Louvain only when reproducing older analyses that required it. [Traag et al. 2019]

The `resolution` parameter controls cluster granularity: lower values (0.1–0.5) produce fewer larger clusters, higher values (0.5–2.0) produce more finer-grained clusters. For most PBMC datasets, 0.5–1.0 is a good starting range.
