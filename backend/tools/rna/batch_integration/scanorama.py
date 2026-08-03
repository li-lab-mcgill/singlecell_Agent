"""Scanorama joint embedding for batch integration."""

from __future__ import annotations


def run(
    adata,
    *,
    batch_key: str,
    n_components: int = 50,
):
    import numpy as np
    import scanorama

    if batch_key not in adata.obs:
        raise ValueError(f"batch_key '{batch_key}' not found in adata.obs.")

    batches = adata.obs[batch_key].unique().tolist()
    splits = [adata[adata.obs[batch_key] == b].copy() for b in batches]
    scanorama.integrate_scanpy(splits, dimred=n_components)
    out = np.vstack([s.obsm["X_scanorama"] for s in splits])

    order = []
    for b in batches:
        order.extend(adata.obs.index[adata.obs[batch_key] == b].tolist())
    pos = {name: i for i, name in enumerate(order)}
    reorder = [pos[name] for name in adata.obs.index]
    adata.obsm["X_scanorama"] = out[reorder]
    if adata.obsm["X_scanorama"].shape[0] != adata.n_obs:
        raise RuntimeError(
            f"Scanorama output has shape {adata.obsm['X_scanorama'].shape}, "
            f"expected first dimension n_obs={adata.n_obs}."
        )
    adata.uns["batch_integration"] = {
        "method": "scanorama",
        "batch_key": batch_key,
        "input": "expression",
        "obsm_key": "X_scanorama",
    }
    return adata
