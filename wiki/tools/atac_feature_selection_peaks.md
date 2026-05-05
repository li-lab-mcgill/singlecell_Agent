---
type: tool
id: atac_feature_selection_peaks
stage: feature_selection
modality: atac
backend: backend/tools/atac/feature_selection/peaks.py
---

Selects highly variable peaks for ATAC dimensionality reduction. Filters the peak matrix to peaks that are accessible in a biologically informative fraction of cells.

Key parameters:
- `n_top_features` (default 50000): number of top variable peaks to retain; 50k is standard for human genome
- `min_cells_pct` (default 0.01): minimum fraction of cells with peak accessible (filters noise peaks)
- `max_cells_pct` (default 0.99): maximum fraction of cells with peak accessible (filters constitutive/housekeeping peaks)

Uses SnapATAC2's `snap.pp.select_features()` internally. Marks selected peaks in `adata.var["selected"]`.

For tile matrices (500 bp bins), the number of features can be reduced to 200,000–500,000 bins; the `min_cells_pct` filter removes uninformative bins.

Package: [[packages/snapatac2]]
Method: [[methods/highly_variable_peaks]]
