---
type: package
id: macs3
version: ">=3.0"
citation: Zhang et al. 2008 Genome Biology; Xu et al. 2023
---

MACS3 (Model-based Analysis of ChIP-seq, version 3) is the standard peak calling tool for ATAC-seq and ChIP-seq data. It identifies genomic regions of open chromatin by modeling the shift size and calling significant enrichments.

Install: `pip install macs3`

MACS3 is invoked as a command-line tool or through SnapATAC2's `snap.tl.macs3()` wrapper. For single-cell ATAC-seq peak calling, the recommended workflow is pseudo-bulk: aggregate fragments per cluster, then call peaks per cluster, then merge into a consensus peak set.

Key parameters:
- `--format BEDPE` — required for paired-end ATAC-seq fragments
- `--nomodel --shift -100 --extsize 200` — standard ATAC-seq settings that shift reads to account for Tn5 transposase insertion
- `--qvalue 0.05` — FDR threshold for peak calling
- `--nolambda` — disable local lambda adjustment; sometimes improves sensitivity for sparse single-cell data

Output: `narrowPeak` file with columns chr, start, end, name, score, strand, signalValue, pValue, qValue, peak.

MACS3 supersedes MACS2 with improved speed and Python 3 compatibility. For new analyses, always use MACS3. MACS2 is retained only for reproducing older published results.
