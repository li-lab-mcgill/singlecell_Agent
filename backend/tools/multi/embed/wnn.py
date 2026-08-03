"""Multi-omic joint embedding via Weighted Nearest Neighbor (WNN).

WNN computes a cell-specific weighting between modality KNN graphs, giving
more weight to the modality that is more informative for each individual cell.
Implemented via muon, which closely follows the Seurat WNN method.

Reference: Hao et al. 2021 (Cell) — Seurat v4 WNN
"""

from __future__ import annotations

from pathlib import Path


def run(
    adata,
    *,
    atac_h5ad_path: str | Path | None = None,
    rna_embedding_key: str = "X_pca",
    atac_embedding_key: str = "X_lsi",
    n_neighbors: int = 20,
    n_pcs_rna: int = 30,
    n_pcs_atac: int = 30,
    embedding_key: str = "X_wnn_umap",
) -> object:
    """Compute WNN joint graph and UMAP from paired RNA+ATAC embeddings.

    RNA and ATAC modalities must each have an embedding computed beforehand
    (e.g. PCA for RNA, LSI for ATAC). WNN computes per-cell modality weights
    and builds a joint KNN graph stored in adata.obsp["connectivities"].

    Args:
        adata: RNA AnnData with RNA embedding in adata.obsm[rna_embedding_key].
               Must share barcodes with ATAC adata.
        atac_h5ad_path: Path to paired ATAC AnnData. If None, reads from
                        adata.uns["atac_h5ad_path"].
        rna_embedding_key: Key in adata.obsm for RNA embedding (default "X_pca").
        atac_embedding_key: Key in atac.obsm for ATAC embedding (default "X_lsi").
        n_neighbors: Number of neighbors for KNN graph (default 20).
        n_pcs_rna: Number of PCs to use from RNA embedding (default 30).
        n_pcs_atac: Number of PCs to use from ATAC embedding (default 30).

    Returns:
        adata with:
        - adata.obsm["X_wnn_umap"]: WNN UMAP embedding (2D)
        - adata.obsp["connectivities"]: WNN joint KNN connectivities
        - adata.obsp["distances"]: WNN joint KNN distances
        - adata.uns["wnn"]: WNN metadata
    """
    import anndata as ad
    import muon as mu
    import numpy as np

    atac_path = _resolve_atac_path(adata, atac_h5ad_path)
    atac = ad.read_h5ad(atac_path)

    _validate_paired(adata, atac)
    _check_embedding(adata, rna_embedding_key, "RNA")
    _check_embedding(atac, atac_embedding_key, "ATAC")

    # Build MuData
    mdata = mu.MuData({"rna": adata, "atac": atac})

    # Copy embeddings into MuData
    mdata["rna"].obsm[rna_embedding_key] = adata.obsm[rna_embedding_key]
    mdata["atac"].obsm[atac_embedding_key] = atac.obsm[atac_embedding_key]

    # Compute per-modality neighbors using scanpy
    import scanpy as sc
    sc.pp.neighbors(
        mdata["rna"],
        use_rep=rna_embedding_key,
        n_neighbors=n_neighbors,
        n_pcs=min(n_pcs_rna, adata.obsm[rna_embedding_key].shape[1]),
    )
    sc.pp.neighbors(
        mdata["atac"],
        use_rep=atac_embedding_key,
        n_neighbors=n_neighbors,
        n_pcs=min(n_pcs_atac, atac.obsm[atac_embedding_key].shape[1]),
    )

    # Compute WNN graph across modalities
    mu.pp.neighbors(mdata)

    # Compute UMAP on WNN graph using muon's umap (compatible with MuData)
    mu.tl.umap(mdata, min_dist=0.3)

    # Copy WNN results back into RNA adata
    adata.obsp["connectivities"] = mdata.obsp.get("connectivities", mdata.obsp.get("rna|atac:connectivities"))
    adata.obsp["distances"] = mdata.obsp.get("distances", mdata.obsp.get("rna|atac:distances"))
    adata.uns["neighbors"] = mdata.uns.get("neighbors", {})

    if "X_umap" in mdata.obsm:
        adata.obsm[embedding_key] = mdata.obsm["X_umap"]
    if embedding_key not in adata.obsm or adata.obsm[embedding_key].shape[0] != adata.n_obs:
        raise RuntimeError(f"WNN UMAP output '{embedding_key}' was not created with n_obs={adata.n_obs} rows.")

    adata.uns["wnn"] = {
        "rna_embedding_key": rna_embedding_key,
        "atac_embedding_key": atac_embedding_key,
        "n_neighbors": n_neighbors,
        "embedding_key": embedding_key,
    }
    adata.uns["embedding"] = {
        "method": "wnn",
        "rna_embedding_key": rna_embedding_key,
        "atac_embedding_key": atac_embedding_key,
        "obsm_key": embedding_key,
    }
    adata.uns["atac_h5ad_path"] = str(atac_path)

    return adata


def _resolve_atac_path(adata, explicit_path) -> Path:
    if explicit_path is not None:
        p = Path(explicit_path)
        if not p.exists():
            raise FileNotFoundError(f"ATAC AnnData not found: {p}")
        return p
    stored = adata.uns.get("atac_h5ad_path")
    if stored is None:
        raise ValueError(
            "atac_h5ad_path must be provided or stored in adata.uns['atac_h5ad_path']. "
            "Run multi_qc_intersect first."
        )
    p = Path(stored)
    if not p.exists():
        raise FileNotFoundError(f"atac_h5ad_path in adata.uns not found: {p}")
    return p


def _validate_paired(rna, atac) -> None:
    if rna.n_obs != atac.n_obs or not all(rna.obs_names == atac.obs_names):
        raise ValueError(
            "RNA and ATAC barcodes don't match. Run multi_qc_intersect first."
        )


def _check_embedding(adata, key, name) -> None:
    if key not in adata.obsm:
        raise ValueError(
            f"{name} embedding '{key}' not found in adata.obsm. "
            f"Run the {name} embedding step first. "
            f"Available: {list(adata.obsm.keys())}"
        )
