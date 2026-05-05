"""Select highly variable peaks for ATAC dimensionality reduction."""

from __future__ import annotations


def run(
    adata,
    *,
    n_features: int = 50_000,
    filter_lower_quantile: float = 0.005,
    filter_upper_quantile: float = 0.005,
) -> object:
    """Select the most informative peaks using snapatac2's feature selection.

    Filters out peaks in the lowest and highest count quantiles (likely
    background or PCR artifacts), then selects the top n_features most
    variable peaks. Selection stored in adata.var["selected"].

    Args:
        adata: AnnData with peak accessibility matrix (cells × peaks).
        n_features: Number of peaks to select (default 50,000).
        filter_lower_quantile: Remove peaks in the bottom quantile by total
                               count (default 0.005 = bottom 0.5%).
        filter_upper_quantile: Remove peaks in the top quantile by total
                               count (default 0.005 = top 0.5%).

    Returns:
        adata subsetted to selected peaks, with adata.var["selected"] column.
    """
    import snapatac2 as snap

    snap.pp.select_features(
        adata,
        n_features=n_features,
        filter_lower_quantile=filter_lower_quantile,
        filter_upper_quantile=filter_upper_quantile,
        inplace=True,
    )

    # Subset to selected features
    if "selected" in adata.var.columns:
        adata = adata[:, adata.var["selected"]].copy()

    return adata
