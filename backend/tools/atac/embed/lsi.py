"""TF-IDF + LSI dimensionality reduction for ATAC data."""

from __future__ import annotations


def run(
    adata,
    *,
    method: str = "tfidf_lsi_v3",
    n_components: int = 50,
    drop_first: bool = True,
    binarize: bool = True,
    random_seed: int = 0,
    scale_factor: float = 10_000.0,
):
    from backend.atac._tfidf_lsi import _run_tfidf_lsi
    return _run_tfidf_lsi(
        adata, method=method, n_components=n_components,
        drop_first=drop_first, binarize=binarize,
        random_seed=random_seed, scale_factor=scale_factor,
    )
