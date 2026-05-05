"""PCA linear dimensionality reduction."""

from __future__ import annotations


def run(
    adata,
    *,
    n_pcs: int = 50,
    random_seed: int = 42,
):
    import scanpy as sc

    sc.pp.pca(adata, n_comps=n_pcs, random_state=random_seed)
    adata.uns["embedding"] = {"method": "pca", "n_pcs": n_pcs, "obsm_key": "X_pca"}
    return adata
