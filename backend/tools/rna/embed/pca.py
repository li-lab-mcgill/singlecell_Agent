"""PCA linear dimensionality reduction."""

from __future__ import annotations


def run(
    adata,
    *,
    n_pcs: int = 50,
    random_seed: int = 42,
    embedding_key: str = "X_pca",
):
    import scanpy as sc

    sc.pp.pca(adata, n_comps=n_pcs, random_state=random_seed)
    if embedding_key != "X_pca":
        adata.obsm[embedding_key] = adata.obsm["X_pca"]
    if adata.obsm[embedding_key].shape[0] != adata.n_obs:
        raise RuntimeError(
            f"PCA output '{embedding_key}' has shape {adata.obsm[embedding_key].shape}, "
            f"expected first dimension n_obs={adata.n_obs}."
        )
    adata.uns["embedding"] = {"method": "pca", "n_pcs": n_pcs, "obsm_key": embedding_key}
    return adata
