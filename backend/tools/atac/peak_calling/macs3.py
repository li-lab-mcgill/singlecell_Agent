"""Peak calling using MACS3 via snapatac2.

Uses snap.tl.macs3() which wraps MACS3 internally. Results are stored
in adata.uns["macs3"] and the merged peak set written to output_dir.
"""

from __future__ import annotations

from pathlib import Path


def run(
    adata,
    *,
    group_key: str | None = None,
    q_value: float = 0.05,
    output_dir: Path | None = None,
) -> object:
    """Call peaks with MACS3 via snapatac2.

    Args:
        adata: AnnData (snapatac2 format with fragment data loaded).
               Fragment file must have been loaded during data import.
        group_key: adata.obs column for pseudo-bulk peak calling per group
                   (e.g. "leiden"). If None, calls peaks on all cells merged.
        q_value: MACS3 q-value cutoff (default 0.05).
        output_dir: If provided, writes merged peak BED file here.

    Returns:
        adata with adata.uns["macs3"] containing peak calls per group,
        and adata.uns["peaks_path"] if output_dir was provided.
    """
    import snapatac2 as snap

    snap.tl.macs3(
        adata,
        groupby=group_key,
        qvalue=q_value,
        key_added="macs3",
        inplace=True,
    )
    # Results in adata.uns["macs3"]: dict of {group: GenomicRanges or BED-like}

    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        peaks_path = output_dir / "peaks_macs3.bed"
        _write_peaks_bed(adata.uns["macs3"], peaks_path)
        adata.uns["peaks_path"] = str(peaks_path)

    return adata


def _write_peaks_bed(macs3_result: dict, out_path: Path) -> None:
    """Write merged peak set from snap.tl.macs3 result to BED file."""
    import pandas as pd

    rows = []
    for group, peaks in macs3_result.items():
        if hasattr(peaks, "to_pandas"):
            df = peaks.to_pandas()
        elif hasattr(peaks, "to_frame"):
            df = peaks.to_frame()
        else:
            continue
        rows.append(df)

    if rows:
        merged = pd.concat(rows, ignore_index=True).drop_duplicates()
        # Expect columns: chrom/chr, chromStart/start, chromEnd/end
        col_map = {}
        for col in merged.columns:
            if col.lower() in ("chrom", "chr", "chromosome"):
                col_map[col] = "chrom"
            elif col.lower() in ("chromstart", "start"):
                col_map[col] = "start"
            elif col.lower() in ("chromend", "end"):
                col_map[col] = "end"
        merged = merged.rename(columns=col_map)
        if {"chrom", "start", "end"}.issubset(merged.columns):
            merged[["chrom", "start", "end"]].to_csv(
                out_path, sep="\t", header=False, index=False
            )
