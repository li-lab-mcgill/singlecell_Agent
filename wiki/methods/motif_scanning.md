---
type: method
id: motif_scanning
label: TF Motif Scanning (Chromatin Accessibility)
---

Motif scanning scores every peak against a database of TF position weight matrices (PWMs), producing a TF × cell matrix of motif accessibility scores. This matrix is used for TF activity inference.

Two components:
1. **Motif-to-peak mapping**: for each peak, scan the underlying genomic sequence for PWM matches above a threshold; produces a binary (motif × peak) matrix
2. **Per-cell activity**: multiply the (peak × cell) accessibility matrix by the (motif × peak) binary matrix → weighted sum of accessible peaks containing each motif per cell

This "chromVAR" approach (or SnapATAC2's equivalent) produces a (cells × TF) activity matrix where each value reflects the deviation in motif accessibility for that TF in that cell.

Output stored in `adata.obsm["X_motif_accessibility"]` or in a separate TF AnnData.

Edges:
No executable backend tool currently exposes standalone motif scanning.
