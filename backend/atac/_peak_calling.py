"""ATAC peak calling: MACS2, MACS3, ArchR iterative, snapATAC2."""

from __future__ import annotations

import gzip
import shutil
import tempfile
from pathlib import Path
from typing import Any

from ..types import PeakCallResult

KNOWN_METHODS = ("macs2", "macs3", "archr_iter", "snapatac2")


def dispatch(
    *,
    fragments_path: Path,
    output_peaks_path: Path,
    method: str,
    refs=None,
    runners=None,
    genome_size: str = "hs",
    q_value: float = 0.05,
    **kwargs: Any,
) -> PeakCallResult:
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown atac.peak_calling method: {method}. Choose from {KNOWN_METHODS}.")
    if method in {"macs2", "macs3"}:
        return _run_macs(
            fragments_path=fragments_path,
            output_peaks_path=output_peaks_path,
            method=method,
            genome_size=genome_size,
            q_value=q_value,
            runners=runners,
        )
    raise NotImplementedError(
        f"atac.peak_calling(method='{method}') is not implemented yet. "
        "ArchR iterative requires R; snapatac2 requires snapatac2-specific input handling."
    )


def _run_macs(
    *,
    fragments_path: Path,
    output_peaks_path: Path,
    method: str,
    genome_size: str,
    q_value: float,
    runners,
) -> PeakCallResult:
    fragments_path = Path(fragments_path)
    output_peaks_path = Path(output_peaks_path)
    if not fragments_path.is_file():
        raise FileNotFoundError(f"fragments_path does not exist: {fragments_path}")
    if runners is None or getattr(runners, "cli", None) is None:
        raise RuntimeError(f"{method} peak calling requires the CLI runner.")
    binary = method
    which = getattr(runners.cli, "which", None)
    if which is not None and which(binary) is None:
        raise FileNotFoundError(f"CLI binary not found on PATH: {binary}")

    output_peaks_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"{method}_peaks_") as tmpdir:
        outdir = Path(tmpdir)
        macs_input = outdir / "fragments.bed"
        n_input_intervals = _write_macs_bed_input(fragments_path, macs_input)
        runners.cli.run(
            [
                binary,
                "callpeak",
                "-t",
                str(macs_input),
                "-f",
                "BED",
                "-g",
                genome_size,
                "-q",
                str(q_value),
                "--outdir",
                str(outdir),
                "-n",
                "peaks",
                "--nomodel",
                "--keep-dup",
                "all",
            ],
            timeout=7200,
        )
        peaks_file = outdir / "peaks_peaks.narrowPeak"
        if not peaks_file.is_file() or peaks_file.stat().st_size == 0:
            raise RuntimeError(f"{method} completed but did not produce a non-empty peaks_peaks.narrowPeak.")
        shutil.copyfile(peaks_file, output_peaks_path)

    n_peaks = _count_nonempty_lines(output_peaks_path)
    return PeakCallResult(
        method=method,
        peaks_path=output_peaks_path,
        n_peaks=n_peaks,
        metrics={
            "fragments_path": str(fragments_path),
            "macs_input_format": "BED",
            "n_input_intervals": n_input_intervals,
            "genome_size": genome_size,
            "q_value": q_value,
            "format": "narrowPeak",
        },
    )


def _count_nonempty_lines(path: Path) -> int:
    with path.open("rt", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def _write_macs_bed_input(fragments_path: Path, output_bed: Path) -> int:
    n_written = 0
    with _open_fragment_text(fragments_path) as src, output_bed.open("wt", encoding="utf-8") as out:
        for line in src:
            if not line or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            try:
                start = int(parts[1])
                end = int(parts[2])
                count = int(parts[4]) if len(parts) >= 5 and parts[4] else 1
            except ValueError:
                continue
            if end <= start or count <= 0:
                continue
            # 10x fragments are chrom/start/end/barcode/count intervals, not
            # BEDPE records. Expand the duplicate count so MACS sees depth.
            for _ in range(count):
                out.write(f"{parts[0]}\t{start}\t{end}\n")
                n_written += 1
    if n_written == 0:
        raise ValueError(f"No valid fragment intervals found in {fragments_path}.")
    return n_written


def _open_fragment_text(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("rt", encoding="utf-8")
