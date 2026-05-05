"""Marker-based cell type annotation using CellMarker v2 database."""

from __future__ import annotations


def run(
    adata,
    *,
    refs,
    obs_cluster: str,
    species: str,
    tissue_type: str,
    cancer_type: str = "Normal",
    top_n_markers: int = 50,
):
    import scanpy as sc

    if refs is None:
        raise RuntimeError("cellmarker requires refs (ReferenceStore) to load CellMarker v2.")
    if obs_cluster not in adata.obs:
        raise ValueError(f"obs_cluster '{obs_cluster}' not in adata.obs.")

    marker_df = refs.get_marker_db("cellmarker_v2")
    sc.tl.rank_genes_groups(adata, obs_cluster, method="wilcoxon")
    rank = adata.uns["rank_genes_groups"]
    groups = rank["names"].dtype.names

    filtered = marker_df
    if "species" in filtered.columns:
        filtered = filtered[filtered["species"].str.lower().str.contains(species.lower(), na=False)]
    if "tissue_type" in filtered.columns:
        filtered = filtered[filtered["tissue_type"].str.lower().str.contains(tissue_type.lower(), na=False)]
    if "cancer_type" in filtered.columns:
        filtered = filtered[filtered["cancer_type"].str.lower().str.contains(cancer_type.lower(), na=False)]

    gene_col = next((c for c in ["Symbol", "Gene name", "marker"] if c in filtered.columns), None)
    cell_col = next((c for c in ["cell_name", "cell type", "cell_type"] if c in filtered.columns), None)
    if gene_col is None or cell_col is None:
        raise RuntimeError(f"CellMarker DataFrame missing expected columns; has: {filtered.columns.tolist()}")

    assigned: dict[str, str] = {}
    for group in groups:
        top_genes = [str(g) for g in rank["names"][group][:top_n_markers]]
        scores: dict[str, int] = {}
        for _, row in filtered.iterrows():
            if str(row[gene_col]) in top_genes:
                scores[str(row[cell_col])] = scores.get(str(row[cell_col]), 0) + 1
        assigned[group] = max(scores, key=scores.get) if scores else "Unknown"

    adata.obs[f"{obs_cluster}_celltype"] = adata.obs[obs_cluster].astype(str).map(assigned)
    adata.uns["annotation"] = {
        "method": "cellmarker",
        "obs_cluster": obs_cluster,
        "species": species,
        "tissue_type": tissue_type,
        "cancer_type": cancer_type,
        "cluster_to_celltype": assigned,
    }
    return adata
