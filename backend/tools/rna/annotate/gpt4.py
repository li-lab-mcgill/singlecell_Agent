"""LLM-based cell type annotation using GPT-4 and top marker genes per cluster."""

from __future__ import annotations


def run(
    adata,
    *,
    obs_cluster: str,
    species: str,
    tissue_type: str,
    openai_api_key: str | None = None,
    top_n_markers: int = 20,
):
    import os
    import scanpy as sc
    from openai import OpenAI

    if obs_cluster not in adata.obs:
        raise ValueError(f"obs_cluster '{obs_cluster}' not in adata.obs.")
    api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set and no openai_api_key passed.")

    sc.tl.rank_genes_groups(adata, obs_cluster, method="wilcoxon")
    rank = adata.uns["rank_genes_groups"]
    groups = rank["names"].dtype.names
    top_markers = {g: [str(x) for x in rank["names"][g][:top_n_markers]] for g in groups}

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

    adata.obs[f"{obs_cluster}_celltype"] = adata.obs[obs_cluster].astype(str).map(assigned)
    adata.uns["annotation"] = {
        "method": "gpt4",
        "obs_cluster": obs_cluster,
        "cluster_to_celltype": assigned,
    }
    return adata
