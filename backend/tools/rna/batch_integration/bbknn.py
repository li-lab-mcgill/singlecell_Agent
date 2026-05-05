"""BBKNN batch-aware graph-based batch correction."""

from __future__ import annotations


def run(
    adata,
    *,
    batch_key: str,
    embedding_key: str = "X_pca",
    neighbors_within_batch: int = 3,
    n_pcs: int = 50,
):
    import bbknn
    import scanpy as sc

    if batch_key not in adata.obs:
        raise ValueError(f"batch_key '{batch_key}' not found in adata.obs.")
    if embedding_key not in adata.obsm:
        if embedding_key == "X_pca":
            sc.pp.pca(adata, n_comps=n_pcs)
        else:
            raise ValueError(f"embedding_key '{embedding_key}' not found in adata.obsm.")

    bbknn.bbknn(
        adata,
        batch_key=batch_key,
        neighbors_within_batch=neighbors_within_batch,
        n_pcs=n_pcs,
        use_rep=embedding_key,
    )
    adata.uns["batch_integration"] = {
        "method": "bbknn",
        "batch_key": batch_key,
        "input_embedding_key": embedding_key,
        "obsm_key": None,
        "modifies": "neighbors",
    }
    return adata
