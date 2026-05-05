---
type: method
id: library_size_normalization
label: Library Size Normalization
---

Library size normalization scales each cell's counts to a common total, removing variation introduced by differences in sequencing depth or capture efficiency.

The standard approach (scanpy default) scales each cell to 10,000 total counts (CPM-like), producing counts per 10k. This preserves relative expression ratios between genes within a cell.

Mathematically: for cell i with total counts T_i, normalized count for gene g is: `(count_ig / T_i) × 10000`

After normalization, `sc.pp.log1p()` applies a log(1+x) transformation. This compresses the dynamic range, makes variance approximately uniform across genes, and is required before PCA.

The normalized+log-transformed matrix is stored in `adata.X` (or `adata.layers["lognorm"]`). Raw counts should be preserved in `adata.layers["counts"]` before normalization for use by count-based models (scVI, DESeq2).

Edges:
- [[tools/rna_normalize_log1p]] implements
