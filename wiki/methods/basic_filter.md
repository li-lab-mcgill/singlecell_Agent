---
type: method
id: basic_filter
label: Basic Cell and Gene Filtering
---

Basic filtering removes cells with extreme QC metrics and genes detected in too few cells. It is the first operation in any QC pipeline.

For RNA, standard thresholds:
- Minimum genes per cell: 200 (removes empty droplets)
- Maximum genes per cell: dataset-dependent upper bound (removes doublets / outliers)
- Minimum cells per gene: 3 (removes noise features)
- Maximum mitochondrial fraction: typically 0.05–0.20 depending on cell type (cardiomyocytes tolerate higher)

For ATAC, equivalent thresholds:
- Minimum fragments per cell: 1000
- Minimum TSS enrichment score: 4.0 (removes low-quality barcodes)
- Nucleosome signal (fragment length ratio): < 4 (removes cells with poor nucleosome-free enrichment)

Thresholds should be set by inspecting per-cell QC metric distributions (violin plots, scatter plots) rather than using fixed cutoffs blindly. Adaptive thresholds based on mean ± N×MAD are more robust than hard cutoffs.

Edges:
- [[tools/rna_qc_basic]] implements
- [[tools/atac_qc_basic]] implements
