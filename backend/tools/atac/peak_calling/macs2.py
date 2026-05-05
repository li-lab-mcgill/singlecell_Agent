"""Peak calling using MACS2 via subprocess.

snapatac2 v2 only wraps MACS3 natively. MACS2 is called here via subprocess
for reproducibility with older pipelines. Requires macs2 to be installed
and on PATH (pip install MACS2).

For new analyses, use atac_peak_calling_macs3 instead.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def run(
    adata,
    *,
    fragments_path: str | Path | None = None,
    group_key: str | None = None,
    genome_size: str = "hs",
    q_value: float = 0.05,
    output_dir: Path | None = None,
) -> object:
    """Call peaks with MACS2 via subprocess.

    Args:
        adata: AnnData. Fragment file read from adata.uns["fragments_path"]
               or passed explicitly.
        fragments_path: Path to fragment file (bgzipped, tabix-indexed).
                        If None, reads from adata.uns["fragments_path"].
        group_key: Ignored for MACS2 (merged peak calling only). Included for
                   API consistency with macs3.
        genome_size: MACS2 genome size — "hs" (human, default), "mm" (mouse),
                     or a numeric string.
        q_value: MACS2 q-value cutoff (default 0.05).
        output_dir: Directory for peak output files. Required.

    Returns:
        adata with adata.uns["peaks_path"] set to the narrowPeak output file.
    """
    frag_path = _resolve_fragments_path(adata, fragments_path)

    if output_dir is None:
        raise ValueError("output_dir is required for MACS2 peak calling.")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    _check_macs2()

    cmd = [
        "macs2", "callpeak",
        "-t", str(frag_path),
        "-f", "BEDPE",
        "-g", genome_size,
        "-q", str(q_value),
        "--nomodel",
        "--shift", "-100",
        "--extsize", "200",
        "--keep-dup", "all",
        "-n", "macs2",
        "--outdir", str(output_dir),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"MACS2 failed:\n{result.stderr}")

    peaks_path = output_dir / "macs2_peaks.narrowPeak"
    if not peaks_path.exists():
        # Try alternative name
        peaks_path = next(output_dir.glob("*.narrowPeak"), None)
        if peaks_path is None:
            raise RuntimeError(f"MACS2 ran but no narrowPeak file found in {output_dir}")

    adata.uns["peaks_path"] = str(peaks_path)
    adata.uns["fragments_path"] = str(frag_path)

    return adata


def _check_macs2() -> None:
    result = subprocess.run(["macs2", "--version"], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "MACS2 not found on PATH. Install with: pip install MACS2\n"
            "For new analyses, consider using atac_peak_calling_macs3 instead."
        )


def _resolve_fragments_path(adata, explicit_path) -> Path:
    if explicit_path is not None:
        p = Path(explicit_path)
        if not p.exists():
            raise FileNotFoundError(f"fragments_path not found: {p}")
        return p
    stored = adata.uns.get("fragments_path")
    if stored is None:
        raise ValueError(
            "fragments_path must be provided or stored in adata.uns['fragments_path']."
        )
    p = Path(stored)
    if not p.exists():
        raise FileNotFoundError(f"fragments_path in adata.uns not found: {p}")
    return p
