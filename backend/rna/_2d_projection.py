"""2D projection for visualization: UMAP, t-SNE, ForceAtlas."""

from __future__ import annotations

from typing import Any

KNOWN_METHODS = ("umap", "tsne", "fa")


def dispatch(adata, *, method: str, embedding_key: str, n_neighbors: int = 15, random_seed: int = 42, **kwargs: Any):
    if embedding_key not in adata.obsm:
        raise ValueError(f"embedding_key '{embedding_key}' not in adata.obsm.")
    import scanpy as sc

    sc.pp.neighbors(adata, n_neighbors=n_neighbors, use_rep=embedding_key)
    if method == "umap":
        sc.tl.umap(adata, random_state=random_seed)
        adata.uns["projection"] = {"method": "umap", "obsm_key": "X_umap"}
    elif method == "tsne":
        sc.tl.tsne(adata, use_rep=embedding_key, random_state=random_seed)
        adata.uns["projection"] = {"method": "tsne", "obsm_key": "X_tsne"}
    elif method == "fa":
        sc.tl.draw_graph(adata, layout="fa", random_state=random_seed)
        adata.uns["projection"] = {"method": "fa", "obsm_key": "X_draw_graph_fa"}
    else:
        raise ValueError(f"Unknown rna.visualize method: {method}. Choose from {KNOWN_METHODS}.")
    return adata
