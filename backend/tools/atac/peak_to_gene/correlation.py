"""Correlation-based peak-to-gene linking.

Correlates ATAC peak accessibility with RNA gene expression across paired cells.
snap.tl.link_peaks() does not exist in snapatac2 v2; implemented directly
with scipy for correctness and portability.

Requires paired RNA AnnData (same cells, same order).
"""

from __future__ import annotations

from pathlib import Path


def run(
    adata,
    *,
    rna_h5ad_path: str | Path | None = None,
    max_distance: int = 500_000,
    min_correlation: float = 0.05,
    gtf_path: str | Path | None = None,
    output_dir: Path | None = None,
) -> object:
    """Link ATAC peaks to genes by Pearson correlation with RNA expression.

    For each gene, finds all peaks within max_distance of its TSS, then
    computes Pearson correlation between peak accessibility and gene expression
    across all cells. Only links with |r| >= min_correlation are kept.

    Args:
        adata: ATAC AnnData with peak accessibility matrix.
               Peak names in adata.var_names must be in "chr:start-end" format.
        rna_h5ad_path: Path to paired RNA AnnData (.h5ad). Must have the same
                       cells in the same order as adata. If None, reads from
                       adata.uns["rna_adata_path"].
        max_distance: Max distance (bp) from gene TSS to consider a peak (default 500,000).
        min_correlation: Minimum |Pearson r| to retain a link (default 0.05).
        gtf_path: Path to GTF file for gene TSS coordinates. If None, reads
                  from adata.uns["gtf_path"]. Required for distance filtering.
        output_dir: If provided, saves links table as parquet.

    Returns:
        adata with adata.uns["peak_gene_links"]: list of
        {peak, gene, correlation, distance} dicts.
    """
    import anndata as ad
    import numpy as np
    import pandas as pd
    import scipy.sparse as sp
    from scipy.stats import pearsonr

    # Resolve RNA adata
    rna_path = rna_h5ad_path or adata.uns.get("rna_adata_path")
    if rna_path is None:
        raise ValueError(
            "rna_h5ad_path must be provided or stored in adata.uns['rna_adata_path']."
        )
    rna_path = Path(rna_path)
    if not rna_path.exists():
        raise FileNotFoundError(f"RNA AnnData not found: {rna_path}")
    rna = ad.read_h5ad(rna_path)

    if rna.n_obs != adata.n_obs:
        raise ValueError(
            f"RNA adata has {rna.n_obs} cells but ATAC adata has {adata.n_obs}. "
            "Paired cells must match exactly."
        )

    # Parse peak coordinates from var_names (format: chr:start-end)
    peak_coords = _parse_peak_coords(adata.var_names)

    # Get gene TSS coordinates
    gtf = gtf_path or adata.uns.get("gtf_path")
    if gtf is not None:
        gene_tss = _parse_gene_tss(Path(gtf))
    else:
        # Fall back: use all peaks within a fixed window without distance filtering
        gene_tss = None

    # Get dense matrices
    X_atac = adata.X
    if sp.issparse(X_atac):
        X_atac = X_atac.toarray()
    X_rna = rna.X
    if sp.issparse(X_rna):
        X_rna = X_rna.toarray()

    # Compute correlations
    links = []
    for gene_idx, gene in enumerate(rna.var_names):
        rna_vec = X_rna[:, gene_idx]
        if rna_vec.std() < 1e-10:
            continue  # skip non-expressed genes

        tss_chrom, tss_pos = None, None
        if gene_tss is not None and gene in gene_tss:
            tss_chrom, tss_pos = gene_tss[gene]

        for peak_idx, peak in enumerate(adata.var_names):
            if tss_chrom is not None and peak in peak_coords:
                p_chrom, p_start, p_end = peak_coords[peak]
                if p_chrom != tss_chrom:
                    continue
                p_mid = (p_start + p_end) // 2
                dist = abs(p_mid - tss_pos)
                if dist > max_distance:
                    continue
            else:
                dist = None

            atac_vec = X_atac[:, peak_idx]
            if atac_vec.std() < 1e-10:
                continue

            r, _ = pearsonr(atac_vec, rna_vec)
            if abs(r) >= min_correlation:
                links.append({
                    "peak": peak,
                    "gene": gene,
                    "correlation": float(r),
                    "distance": int(dist) if dist is not None else None,
                })

    links_df = pd.DataFrame(links)
    adata.uns["peak_gene_links"] = links_df.to_dict("records")
    adata.uns["rna_adata_path"] = str(rna_path)

    if output_dir is not None and len(links) > 0:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        links_df.to_parquet(output_dir / "peak_gene_links.parquet", index=False)

    return adata


def _parse_peak_coords(var_names) -> dict[str, tuple[str, int, int]]:
    """Parse 'chr1:100-200' → {peak: (chrom, start, end)}."""
    coords = {}
    for name in var_names:
        try:
            chrom, rest = name.rsplit(":", 1)
            start, end = rest.split("-")
            coords[name] = (chrom, int(start), int(end))
        except (ValueError, AttributeError):
            pass
    return coords


def _parse_gene_tss(gtf_path: Path) -> dict[str, tuple[str, int]]:
    """Extract gene TSS positions from GTF. Returns {gene_name: (chrom, tss)}."""
    import gzip

    tss: dict[str, tuple[str, int]] = {}
    opener = gzip.open if str(gtf_path).endswith(".gz") else open

    with opener(gtf_path, "rt") as f:
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.strip().split("\t")
            if len(parts) < 9 or parts[2] != "gene":
                continue
            chrom = parts[0]
            start = int(parts[3])
            end = int(parts[4])
            strand = parts[6]
            attrs = parts[8]

            gene_name = None
            for attr in attrs.split(";"):
                attr = attr.strip()
                if attr.startswith("gene_name"):
                    gene_name = attr.split('"')[1]
                    break

            if gene_name:
                tss_pos = start if strand == "+" else end
                if gene_name not in tss:
                    tss[gene_name] = (chrom, tss_pos)
    return tss
