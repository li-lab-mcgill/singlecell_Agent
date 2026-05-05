---
type: method
id: macs_peak_calling
label: MACS3 Peak Calling
---

MACS3 peak calling identifies genomic regions with significant fragment enrichment above background. For single-cell ATAC, pseudo-bulk peak calling per cluster is standard.

Workflow:
1. For each cluster, extract fragment coordinates for all cells in that cluster
2. Run MACS3 with ATAC-specific parameters: `--format BEDPE --nomodel --shift -100 --extsize 200 --qvalue 0.05`
3. Collect per-cluster narrowPeak files
4. Merge all peaks into a consensus peak set (union of all cluster peaks, then merge overlapping intervals)
5. Re-quantify the consensus peak set across all cells → final cell × peak matrix

This approach captures cell-type-specific regulatory elements that are only accessible in a subset of clusters. Calling peaks on all cells pooled misses cluster-specific peaks.

The Tn5 transposase inserts at both ends of the nucleosome-free region. The `--shift -100 --extsize 200` parameters center peaks on the insertion site by shifting the 5' read end.

SnapATAC2 wraps this workflow in `snap.tl.macs3()` + `snap.tl.merge_peaks()`.

Edges:
- [[tools/atac_peak_calling_macs3]] implements
