"""UMAP 2D projection for ATAC data visualization."""

from __future__ import annotations


def run(
    adata,
    *,
    embedding_key: str = "X_lsi",
    n_neighbors: int = 15,
    random_seed: int = 42,
):
    import scanpy as sc

    if embedding_key not in adata.obsm:
        raise ValueError(f"embedding_key '{embedding_key}' not in adata.obsm.")

    sc.pp.neighbors(adata, n_neighbors=n_neighbors, use_rep=embedding_key)
    sc.tl.umap(adata, random_state=random_seed)
    adata.uns["projection"] = {"method": "umap", "embedding_key": embedding_key, "obsm_key": "X_umap"}
    return adata
