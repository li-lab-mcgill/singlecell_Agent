"""Per-cell annotation using CellTypist pretrained models."""

from __future__ import annotations


def run(
    adata,
    *,
    model: str = "Immune_All_Low.pkl",
    majority_voting: bool = True,
    cluster_key: str | None = None,
    output_key: str = "celltype",
):
    import celltypist

    predictions = celltypist.annotate(adata, model=model, majority_voting=majority_voting)
    annotated = predictions.to_adata()
    if majority_voting and "majority_voting" in annotated.obs:
        label_col = "majority_voting"
    elif "predicted_labels" in annotated.obs:
        label_col = "predicted_labels"
    else:
        # Fallback: take the first obs column produced by celltypist
        label_col = annotated.obs.columns[0]
    col = f"{cluster_key}_celltype" if cluster_key and cluster_key in adata.obs else output_key
    adata.obs[col] = annotated.obs[label_col].values
    adata.uns["annotation"] = {
        "method": "celltypist",
        "model": model,
        "majority_voting": majority_voting,
        "label_column": label_col,
        "output_key": col,
    }
    return adata
