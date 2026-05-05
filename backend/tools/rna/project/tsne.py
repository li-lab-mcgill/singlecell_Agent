"""t-SNE 2D projection for visualization."""

from __future__ import annotations


def run(
    adata,
    *,
    embedding_key: str,
    n_neighbors: int = 15,
    random_seed: int = 42,
):
    import scanpy as sc

    if embedding_key not in adata.obsm:
        raise ValueError(f"embedding_key '{embedding_key}' not in adata.obsm.")

    sc.pp.neighbors(adata, n_neighbors=n_neighbors, use_rep=embedding_key)
    sc.tl.tsne(adata, use_rep=embedding_key, random_state=random_seed)
    adata.uns["projection"] = {"method": "tsne", "embedding_key": embedding_key, "obsm_key": "X_tsne"}
    return adata
