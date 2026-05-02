"""Biology-preservation metrics: bio LISI, marker specificity."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def bio_lisi(adata, embedding_key: str, label_key: str) -> float:
    raise NotImplementedError(
        "TODO: implement bio_lisi. Recommended: scib_metrics.clisi_knn("
        "adata.obsm[embedding_key], labels=adata.obs[label_key])."
    )


def marker_specificity(
    adata,
    cluster_key: str,
    markers: Dict[str, List[str]],
    min_specificity: float = 0.5,
) -> float:
    """Fraction of known cell-type markers that appear among top DE genes of
    the cluster most enriched for that cell type.

    markers: {cell_type_name: [gene_symbols...]}
    """
    import scanpy as sc

    if cluster_key not in adata.obs:
        raise KeyError(f"marker_specificity: cluster '{cluster_key}' not in adata.obs")
    sc.tl.rank_genes_groups(adata, cluster_key, method="wilcoxon")
    rank = adata.uns["rank_genes_groups"]
    cluster_names = list(rank["names"].dtype.names)

    hits = 0
    total = 0
    for cell_type, panel in markers.items():
        if not panel:
            continue
        # Find cluster with most overlap with this cell type's markers.
        best = 0
        for c in cluster_names:
            top = set(str(g) for g in rank["names"][c][:50])
            best = max(best, len(top & set(panel)))
        if len(panel) > 0:
            hits += best
            total += min(len(panel), 50)

    return float(hits) / float(total) if total > 0 else 0.0
