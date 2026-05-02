"""RNA cell type annotation: GPT-4, CellMarker, CellTypist, SingleR, Azimuth, scArches."""

from __future__ import annotations

from typing import Any, Optional

KNOWN_METHODS = ("gpt4", "cellmarker", "celltypist", "singler", "azimuth", "scarches")


def dispatch(adata, *, method: str, refs=None, runners=None, **kwargs: Any):
    if method == "gpt4":
        return _run_gpt4(adata, **kwargs)
    if method == "cellmarker":
        return _run_cellmarker(adata, refs=refs, **kwargs)
    if method == "celltypist":
        return _run_celltypist(adata, **kwargs)
    if method == "singler":
        return _run_singler(adata, refs=refs, runners=runners, **kwargs)
    if method == "azimuth":
        return _run_azimuth(adata, refs=refs, runners=runners, **kwargs)
    if method == "scarches":
        return _run_scarches(adata, refs=refs, **kwargs)
    raise ValueError(f"Unknown rna.annotate method: {method}. Choose from {KNOWN_METHODS}.")


def _run_celltypist(
    adata,
    *,
    model: str = "Immune_All_Low.pkl",
    majority_voting: bool = True,
    obs_cluster: Optional[str] = None,
    **_: Any,
):
    import celltypist

    predictions = celltypist.annotate(adata, model=model, majority_voting=majority_voting)
    annotated = predictions.to_adata()
    label_col = "majority_voting" if majority_voting and "majority_voting" in annotated.obs else "predicted_labels"
    if obs_cluster and obs_cluster in adata.obs:
        adata.obs[f"{obs_cluster}_celltype"] = annotated.obs[label_col].values
    else:
        adata.obs["celltype"] = annotated.obs[label_col].values
    adata.uns["annotation"] = {
        "method": "celltypist",
        "model": model,
        "majority_voting": majority_voting,
        "label_column": label_col,
    }
    return adata


def _run_cellmarker(
    adata,
    *,
    refs,
    obs_cluster: str,
    species: str,
    tissue_type: str,
    cancer_type: str = "Normal",
    top_n_markers: int = 50,
    **_: Any,
):
    import scanpy as sc

    if refs is None:
        raise RuntimeError("cellmarker annotation requires refs (ReferenceStore) to load CellMarker v2.")
    marker_df = refs.get_marker_db("cellmarker_v2")
    if obs_cluster not in adata.obs:
        raise ValueError(f"obs_cluster '{obs_cluster}' not in adata.obs.")

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

    new_col = f"{obs_cluster}_celltype"
    adata.obs[new_col] = adata.obs[obs_cluster].astype(str).map(assigned)
    adata.uns["annotation"] = {
        "method": "cellmarker",
        "obs_cluster": obs_cluster,
        "species": species,
        "tissue_type": tissue_type,
        "cancer_type": cancer_type,
        "cluster_to_celltype": assigned,
    }
    return adata


def _run_gpt4(adata, *, obs_cluster: str, species: str, tissue_type: str, openai_api_key: Optional[str] = None, **_: Any):
    import os

    from openai import OpenAI
    import scanpy as sc

    if obs_cluster not in adata.obs:
        raise ValueError(f"obs_cluster '{obs_cluster}' not in adata.obs.")
    api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set and no openai_api_key passed.")

    sc.tl.rank_genes_groups(adata, obs_cluster, method="wilcoxon")
    rank = adata.uns["rank_genes_groups"]
    groups = rank["names"].dtype.names
    top_markers = {g: [str(x) for x in rank["names"][g][:20]] for g in groups}

    client = OpenAI(api_key=api_key)
    assigned: dict[str, str] = {}
    for group, markers in top_markers.items():
        prompt = (
            f"Given these top marker genes for a single-cell cluster in {species} {tissue_type}: "
            f"{', '.join(markers)}. What cell type is this most likely? Reply with only the cell type name."
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=30,
        )
        assigned[group] = response.choices[0].message.content.strip()

    new_col = f"{obs_cluster}_celltype"
    adata.obs[new_col] = adata.obs[obs_cluster].astype(str).map(assigned)
    adata.uns["annotation"] = {
        "method": "gpt4",
        "obs_cluster": obs_cluster,
        "cluster_to_celltype": assigned,
    }
    return adata


def _run_singler(adata, *, refs, runners, **_: Any):
    raise NotImplementedError("TODO: SingleR via R runner (r_scripts/rna/celltype_annotation_singler.R)")


def _run_azimuth(adata, *, refs, runners, **_: Any):
    raise NotImplementedError("TODO: Azimuth via R runner (r_scripts/rna/celltype_annotation_azimuth.R)")


def _run_scarches(adata, *, refs, **_: Any):
    raise NotImplementedError("TODO: scArches reference mapping (Python, requires pretrained ref model in refs).")
