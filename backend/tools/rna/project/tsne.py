"""t-SNE 2D projection for visualization."""

from __future__ import annotations


def run(
    adata,
    *,
    embedding_key: str,
    n_neighbors: int = 15,
    perplexity: float = 30.0,
    random_seed: int = 42,
    projection_key: str = "X_tsne",
):
    import scanpy as sc

    if embedding_key not in adata.obsm:
        raise ValueError(f"embedding_key '{embedding_key}' not in adata.obsm.")

    sc.pp.neighbors(adata, n_neighbors=n_neighbors, use_rep=embedding_key)
    sc.tl.tsne(adata, use_rep=embedding_key, perplexity=perplexity, random_state=random_seed)
    if projection_key != "X_tsne" and "X_tsne" in adata.obsm:
        adata.obsm[projection_key] = adata.obsm["X_tsne"]
    if projection_key not in adata.obsm or adata.obsm[projection_key].shape[0] != adata.n_obs:
        raise RuntimeError(f"t-SNE output '{projection_key}' was not created with n_obs={adata.n_obs} rows.")
    adata.uns["projection"] = {"method": "tsne", "embedding_key": embedding_key, "obsm_key": projection_key}
    return adata
