"""ATAC peak-to-gene regulatory linking: Cicero, peak2gene, ArchR p2g."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..types import LinkSet
from ._utils import parse_peak_coordinates, require_matrix

KNOWN_METHODS = ("cicero", "peak2gene", "archr_p2g")


def dispatch(
    adata,
    *,
    method: str,
    gene_annotation: str = "gencode_v44_human",
    refs=None,
    runners=None,
    max_distance: int = 500_000,
    **kwargs: Any,
) -> LinkSet:
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown atac.peak_to_gene_linking method: {method}. Choose from {KNOWN_METHODS}.")
    if method == "peak2gene":
        return _run_peak2gene(adata, max_distance=max_distance, **kwargs)
    raise NotImplementedError(
        f"atac.peak_to_gene_linking(method='{method}') is not implemented yet. "
        "Cicero + ArchR p2g via R runner; peak2gene = correlation-based, can be Python."
    )


def _run_peak2gene(
    adata,
    *,
    gene_activity_key: str = "gene_activity",
    gene_names_key: str = "genes",
    gene_coordinates_key: str = "gene_coordinates",
    max_distance: int = 500_000,
    min_correlation: float = 0.0,
    min_abs_correlation: float | None = None,
    allow_negative: bool = False,
    top_n_per_gene: int = 10,
    output_links_path: str | Path | None = None,
    max_links_in_result: int = 100,
    **_: Any,
) -> LinkSet:
    import numpy as np
    from scipy import sparse

    if max_distance <= 0:
        raise ValueError("max_distance must be positive.")
    if top_n_per_gene <= 0:
        raise ValueError("top_n_per_gene must be positive.")

    X = require_matrix(adata)
    peaks = parse_peak_coordinates(adata)
    gene_activity = getattr(adata, "obsm", {}).get(gene_activity_key)
    if gene_activity is None:
        raise ValueError(f"peak2gene requires adata.obsm[{gene_activity_key!r}] with cell x gene activity values.")

    genes, gene_coords = _gene_activity_metadata(
        adata,
        gene_names_key=gene_names_key,
        gene_coordinates_key=gene_coordinates_key,
    )
    if getattr(gene_activity, "shape", None) is None or gene_activity.shape[1] != len(genes):
        raise ValueError(
            f"adata.obsm[{gene_activity_key!r}] columns must match {len(genes)} gene labels; "
            f"got shape={getattr(gene_activity, 'shape', None)}."
        )

    peak_matrix = X.tocsc() if sparse.issparse(X) else np.asarray(X)
    gene_matrix = gene_activity.tocsc() if sparse.issparse(gene_activity) else np.asarray(gene_activity)
    peak_centers = [(chrom, (start + end) // 2, name) for chrom, start, end, name in peaks]

    rows: list[dict[str, Any]] = []
    for gene_index, gene in enumerate(genes):
        gene_coord = gene_coords.get(gene)
        if gene_coord is None:
            continue
        gene_chrom, gene_tss = gene_coord
        gene_values = _column_vector(gene_matrix, gene_index)
        gene_rows = []
        for peak_index, (peak_chrom, peak_center, peak_name) in enumerate(peak_centers):
            if peak_chrom != gene_chrom:
                continue
            distance = abs(peak_center - gene_tss)
            if distance > max_distance:
                continue
            corr = _pearson(_column_vector(peak_matrix, peak_index), gene_values)
            if np.isnan(corr):
                continue
            if allow_negative:
                threshold = min_abs_correlation if min_abs_correlation is not None else abs(min_correlation)
                if abs(corr) < threshold:
                    continue
            elif corr < min_correlation:
                continue
            gene_rows.append(
                {
                    "peak": peak_name,
                    "gene": gene,
                    "chrom": gene_chrom,
                    "distance": int(distance),
                    "correlation": float(corr),
                    "abs_correlation": float(abs(corr)),
                }
            )
        if allow_negative:
            gene_rows.sort(key=lambda row: (-row["abs_correlation"], row["distance"], row["peak"]))
        else:
            gene_rows.sort(key=lambda row: (-row["correlation"], row["distance"], row["peak"]))
        rows.extend(gene_rows[:top_n_per_gene])

    if allow_negative:
        rows.sort(key=lambda row: (-row["abs_correlation"], row["gene"], row["distance"], row["peak"]))
    else:
        rows.sort(key=lambda row: (-row["correlation"], row["gene"], row["distance"], row["peak"]))
    table_path = Path(output_links_path) if output_links_path else None
    if table_path is not None:
        import pandas as pd

        table_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(table_path, index=False)

    return LinkSet(
        method="peak2gene",
        n_links=len(rows),
        links_path=table_path,
        metadata={
            "gene_activity_key": gene_activity_key,
            "gene_names_key": gene_names_key,
            "gene_coordinates_key": gene_coordinates_key,
            "max_distance": max_distance,
            "min_correlation": min_correlation,
            "min_abs_correlation": min_abs_correlation,
            "allow_negative": allow_negative,
            "top_n_per_gene": top_n_per_gene,
            "n_genes_with_coordinates": len(gene_coords),
            "n_peaks": len(peaks),
            "links": rows[:max_links_in_result],
            "links_truncated": len(rows) > max_links_in_result,
        },
    )


def _gene_activity_metadata(
    adata,
    *,
    gene_names_key: str,
    gene_coordinates_key: str,
) -> tuple[list[str], dict[str, tuple[str, int]]]:
    uns = getattr(adata, "uns", {})
    gene_activity_meta = uns.get("gene_activity", {}) if isinstance(uns.get("gene_activity", {}), dict) else {}
    genes = gene_activity_meta.get(gene_names_key, uns.get(gene_names_key))
    if genes is None:
        raise ValueError(
            f"peak2gene requires gene labels in adata.uns['gene_activity'][{gene_names_key!r}] "
            f"or adata.uns[{gene_names_key!r}]."
        )
    coordinates = gene_activity_meta.get(gene_coordinates_key, uns.get(gene_coordinates_key))
    if coordinates is None:
        raise ValueError(
            f"peak2gene requires gene coordinates in adata.uns['gene_activity'][{gene_coordinates_key!r}] "
            f"or adata.uns[{gene_coordinates_key!r}]."
        )
    gene_list = [str(gene) for gene in genes]
    return gene_list, _coerce_gene_coordinates(coordinates)


def _coerce_gene_coordinates(coordinates: Any) -> dict[str, tuple[str, int]]:
    try:
        import pandas as pd
    except Exception:
        pd = None

    if isinstance(coordinates, dict):
        result: dict[str, tuple[str, int]] = {}
        for gene, coord in coordinates.items():
            if isinstance(coord, dict):
                chrom = coord.get("chrom") or coord.get("chr")
                tss = coord.get("tss")
                if tss is None:
                    start = coord.get("start")
                    end = coord.get("end", start)
                    strand = coord.get("strand", "+")
                    tss = end if str(strand) == "-" else start
            else:
                chrom, tss = coord[0], coord[1]
            if chrom is None or tss is None:
                continue
            result[str(gene)] = (str(chrom), int(tss))
        return result

    if pd is not None and isinstance(coordinates, pd.DataFrame):
        columns = {str(column).lower(): column for column in coordinates.columns}
        gene_col = columns.get("gene") or columns.get("gene_name") or columns.get("symbol")
        chrom_col = columns.get("chrom") or columns.get("chr")
        tss_col = columns.get("tss")
        start_col = columns.get("start")
        end_col = columns.get("end")
        strand_col = columns.get("strand")
        if gene_col is None or chrom_col is None or (tss_col is None and start_col is None):
            raise ValueError("gene coordinate DataFrame requires gene, chrom, and tss or start columns.")
        result = {}
        for _, row in coordinates.iterrows():
            if tss_col is not None:
                tss = row[tss_col]
            else:
                strand = row[strand_col] if strand_col is not None else "+"
                tss = row[end_col] if str(strand) == "-" and end_col is not None else row[start_col]
            result[str(row[gene_col])] = (str(row[chrom_col]), int(tss))
        return result

    raise ValueError("gene coordinates must be a dict or pandas DataFrame.")


def _column_vector(matrix: Any, index: int):
    import numpy as np
    from scipy import sparse

    column = matrix[:, index]
    if sparse.issparse(column):
        return np.asarray(column.toarray()).ravel()
    return np.asarray(column).ravel()


def _pearson(x: Any, y: Any) -> float:
    import numpy as np

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.shape[0] != y.shape[0]:
        raise ValueError(f"Cannot correlate vectors with different lengths: {x.shape[0]} and {y.shape[0]}.")
    x = x - x.mean()
    y = y - y.mean()
    denom = float(np.sqrt(np.dot(x, x) * np.dot(y, y)))
    if denom == 0.0:
        return float("nan")
    return float(np.dot(x, y) / denom)
