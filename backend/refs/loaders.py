"""Parsers that turn an on-disk reference file into an in-memory object.

Every loader is a callable ``loader(path: Path) -> Any``. The return type is
category-specific; the ReferenceStore does not inspect it.

Loaders here are intentionally conservative: they prefer lazy / indexed
access (pyfaidx for FASTA, `backed='r'` for AnnData) to keep memory small.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def load_genome_fasta(path: Path) -> Any:
    """Return a pyfaidx.Fasta handle. Keeps an open file + .fai index."""
    try:
        import pyfaidx
    except ImportError as exc:
        raise RuntimeError("pyfaidx is required for genome FASTA loading") from exc
    return pyfaidx.Fasta(str(path), sequence_always_upper=True, as_raw=True)


def load_gtf(path: Path) -> Any:
    """Parse a GTF into a pyranges PyRanges object (or a pandas DataFrame fallback)."""
    try:
        import pyranges as pr
    except ImportError:
        import pandas as pd

        cols = [
            "Chromosome", "Source", "Feature", "Start", "End",
            "Score", "Strand", "Frame", "Attribute",
        ]
        return pd.read_csv(
            path, sep="\t", comment="#", names=cols, low_memory=False,
        )
    return pr.read_gtf(str(path))


def load_bed(path: Path) -> Any:
    try:
        import pyranges as pr
    except ImportError:
        import pandas as pd
        return pd.read_csv(path, sep="\t", header=None, comment="#", low_memory=False)
    return pr.read_bed(str(path))


def load_motifs_meme(path: Path) -> Any:
    """Parse a MEME-format motif file. Returns a list of dict entries with PWMs."""
    motifs: list[dict] = []
    current: dict | None = None
    pwm_rows: list[list[float]] = []
    with open(path, "r") as f:
        for raw in f:
            line = raw.strip()
            if line.startswith("MOTIF"):
                if current is not None:
                    current["pwm"] = pwm_rows
                    motifs.append(current)
                parts = line.split()
                current = {"id": parts[1] if len(parts) > 1 else "", "name": parts[2] if len(parts) > 2 else "", "pwm": []}
                pwm_rows = []
            elif current is not None and line and not line.startswith("letter-probability"):
                tokens = line.split()
                try:
                    vals = [float(t) for t in tokens]
                    if len(vals) == 4:
                        pwm_rows.append(vals)
                except ValueError:
                    continue
        if current is not None:
            current["pwm"] = pwm_rows
            motifs.append(current)
    return motifs


def load_motifs_cisbp(path: Path) -> Any:
    """CIS-BP ships as a zip of PWMs; loader unpacks lazily into a dict."""
    import zipfile

    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as zf:
            return {name: zf.read(name).decode("utf-8") for name in zf.namelist() if name.endswith(".txt")}
    return {path.name: path.read_text()}


def load_cellmarker(path: Path) -> Any:
    """CellMarker v2 xlsx → pandas DataFrame."""
    import pandas as pd
    return pd.read_excel(path)


def load_panglao(path: Path) -> Any:
    import pandas as pd
    return pd.read_csv(path, sep="\t")


def load_lr_tsv(path: Path) -> Any:
    import pandas as pd
    return pd.read_csv(path, sep="\t")


def load_gmt(path: Path) -> dict:
    """Parse a GMT gene-set file into {set_name: [genes]}."""
    sets: dict[str, list[str]] = {}
    with open(path, "r") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            name, _desc, *genes = parts
            sets[name] = [g for g in genes if g]
    return sets


def load_tf_targets_tsv(path: Path) -> Any:
    import pandas as pd
    return pd.read_csv(path, sep="\t") if path.suffix == ".tsv" else pd.read_csv(path)


def load_atlas_backed(path: Path) -> Any:
    """Open a reference AnnData in backed='r' mode (no full load into RAM)."""
    try:
        import anndata as ad
    except ImportError as exc:
        raise RuntimeError("anndata is required for atlas loading") from exc
    return ad.read_h5ad(str(path), backed="r")
