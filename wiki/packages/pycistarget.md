---
type: package
id: pycistarget
version: ">=1.0"
citation: Bravo González-Blas et al. 2023 Nature Methods (SCENIC+)
---

pycistarget performs TF binding motif enrichment analysis on sets of genomic regions using the cisTarget ranking-based method and optionally the Differentially Enriched Motifs (DEM) method. It is the ATAC-side complement to pySCENIC's ctx step, working on arbitrary region sets (e.g. topic-derived sets) rather than gene co-expression modules.

Install: `pip install pycistarget` (included with SCENIC+)

## Methods

**cisTarget (CTX)** — ranking-based enrichment: regions are ranked by motif score using pre-built feather databases; NES (normalized enrichment score) identifies significantly enriched motifs.

**DEM** — differential enrichment: compares motif scores in foreground regions vs. a random background subset. More sensitive for small region sets where ranking is unstable.

## Usage via SCENIC+

In the SCENIC+ workflow, `run_pycistarget()` is imported from `scenicplus.wrappers.run_pycistarget`, **not** from the pycistarget package directly:

```python
from scenicplus.wrappers.run_pycistarget import run_pycistarget
```

Input region sets must be `Dict[str, pr.PyRanges]` — string peak names must be converted first.

## Database version compatibility

The `annotation_version` parameter must match the version of the feather database files:
- Standard `pyscenic_databases` preset uses `v10nr_clust` databases → set `annotation_version='v10nr_clust'`
- Default value in `run_pycistarget()` is `'v9'` — this will silently use the wrong annotation if not overridden

## Output

`run_pycistarget()` returns a nested dict `menr: Dict[topic_name, Dict[method, CisTargetResult]]`. Each `CisTargetResult` has a `.motif_enrichment` DataFrame. The full dict must be pickled to disk for use by `create_SCENICPLUS_object()`.

Required databases: same cisTarget feather files used by pySCENIC. See [[resources/pyscenic_databases]].

Used by: [[tools/multi_grn_pycistarget]]
