"""UMAP 2D projection for visualization."""

from __future__ import annotations


def run(
    adata,
    *,
    embedding_key: str,
    n_neighbors: int = 15,
    min_dist: float = 0.5,
    spread: float = 1.0,
    random_seed: int = 42,
    projection_key: str = "X_umap",
):
    import scanpy as sc

    if embedding_key not in adata.obsm:
        raise ValueError(f"embedding_key '{embedding_key}' not in adata.obsm.")

    sc.pp.neighbors(adata, n_neighbors=n_neighbors, use_rep=embedding_key)
    sc.tl.umap(adata, min_dist=min_dist, spread=spread, random_state=random_seed)
    if projection_key != "X_umap" and "X_umap" in adata.obsm:
        adata.obsm[projection_key] = adata.obsm["X_umap"]
    if projection_key not in adata.obsm or adata.obsm[projection_key].shape[0] != adata.n_obs:
        raise RuntimeError(f"UMAP output '{projection_key}' was not created with n_obs={adata.n_obs} rows.")
    adata.uns["projection"] = {"method": "umap", "embedding_key": embedding_key, "obsm_key": projection_key}
    return adata
