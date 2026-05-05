"""Download utility for pySCENIC cisTarget databases, TF lists, and motif annotations.

Usage from Python:
    from backend.tools.rna.grn.download_databases import download, list_databases

    # List all available databases
    list_databases()

    # Download by alias into a destination directory
    download("hg38_refseq_10kb", dest_dir="~/pyscenic_data")
    download("hg38_refseq_500bp", dest_dir="~/pyscenic_data")
    download("hg38_screen", dest_dir="~/pyscenic_data")
    download("hg38_motifs", dest_dir="~/pyscenic_data")
    download("hg38_tfs", dest_dir="~/pyscenic_data")

    # Download a full preset (all files needed for one organism)
    download_preset("human", dest_dir="~/pyscenic_data")
    download_preset("human_with_screen", dest_dir="~/pyscenic_data")
    download_preset("mouse", dest_dir="~/pyscenic_data")

Usage from CLI:
    python -m backend.tools.rna.grn.download_databases --preset human --dest ~/pyscenic_data
    python -m backend.tools.rna.grn.download_databases --db hg38_refseq_10kb --dest ~/pyscenic_data
    python -m backend.tools.rna.grn.download_databases --list
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import NamedTuple

_BASE = "https://resources.aertslab.org/cistarget"

# --- Database catalog ---

class DBEntry(NamedTuple):
    alias: str
    filename: str
    url: str
    size_gb: float
    description: str


_CATALOG: list[DBEntry] = [
    # Human hg38 — refseq
    DBEntry(
        alias="hg38_refseq_10kb",
        filename="hg38__refseq-r80__10kb_up_and_down_tss.mc9nr.feather",
        url=f"{_BASE}/databases/homo_sapiens/hg38/refseq_r80/mc9nr/gene_based/"
            "hg38__refseq-r80__10kb_up_and_down_tss.mc9nr.feather",
        size_gb=15.4,
        description="Human hg38 — ±10kb around TSS (refseq r80) — standard default",
    ),
    DBEntry(
        alias="hg38_refseq_500bp",
        filename="hg38__refseq-r80__500bp_up_and_100bp_down_tss.mc9nr.feather",
        url=f"{_BASE}/databases/homo_sapiens/hg38/refseq_r80/mc9nr/gene_based/"
            "hg38__refseq-r80__500bp_up_and_100bp_down_tss.mc9nr.feather",
        size_gb=15.4,
        description="Human hg38 — tight promoter 500bp up / 100bp down (refseq r80)",
    ),
    # Human hg38 — SCREEN (ENCODE cCREs)
    DBEntry(
        alias="hg38_screen",
        filename="hg38__SCREEN__v10_clust.genes_vs_motifs.rankings.feather",
        url=f"{_BASE}/databases/homo_sapiens/hg38/screen/mc_v10_clust/region_based/"
            "hg38__SCREEN__v10_clust.genes_vs_motifs.rankings.feather",
        size_gb=17.2,
        description="Human hg38 — ENCODE SCREEN cCREs (distal enhancers + promoters)",
    ),
    # Human hg19 — refseq
    DBEntry(
        alias="hg19_refseq_10kb",
        filename="hg19__refseq-r80__10kb_up_and_down_tss.mc9nr.feather",
        url=f"{_BASE}/databases/homo_sapiens/hg19/refseq_r80/mc9nr/gene_based/"
            "hg19__refseq-r80__10kb_up_and_down_tss.mc9nr.feather",
        size_gb=15.1,
        description="Human hg19 — ±10kb around TSS (refseq r80)",
    ),
    DBEntry(
        alias="hg19_refseq_500bp",
        filename="hg19__refseq-r80__500bp_up_and_100bp_down_tss.mc9nr.feather",
        url=f"{_BASE}/databases/homo_sapiens/hg19/refseq_r80/mc9nr/gene_based/"
            "hg19__refseq-r80__500bp_up_and_100bp_down_tss.mc9nr.feather",
        size_gb=15.1,
        description="Human hg19 — tight promoter 500bp up / 100bp down (refseq r80)",
    ),
    # Mouse mm10 — refseq
    DBEntry(
        alias="mm10_refseq_10kb",
        filename="mm10__refseq-r80__10kb_up_and_down_tss.mc9nr.feather",
        url=f"{_BASE}/databases/mus_musculus/mm10/refseq_r80/mc9nr/gene_based/"
            "mm10__refseq-r80__10kb_up_and_down_tss.mc9nr.feather",
        size_gb=12.6,
        description="Mouse mm10 — ±10kb around TSS (refseq r80)",
    ),
    DBEntry(
        alias="mm10_refseq_500bp",
        filename="mm10__refseq-r80__500bp_up_and_100bp_down_tss.mc9nr.feather",
        url=f"{_BASE}/databases/mus_musculus/mm10/refseq_r80/mc9nr/gene_based/"
            "mm10__refseq-r80__500bp_up_and_100bp_down_tss.mc9nr.feather",
        size_gb=12.6,
        description="Mouse mm10 — tight promoter 500bp up / 100bp down (refseq r80)",
    ),
    # Motif annotations
    DBEntry(
        alias="hg38_motifs",
        filename="motifs-v9-nr.hgnc-m0.001-o0.0.tbl",
        url=f"{_BASE}/motif2tf/motifs-v9-nr.hgnc-m0.001-o0.0.tbl",
        size_gb=0.01,
        description="Motif-to-TF annotation for human (HGNC symbols, v9 motif collection)",
    ),
    DBEntry(
        alias="mm10_motifs",
        filename="motifs-v9-nr.mgi-m0.001-o0.0.tbl",
        url=f"{_BASE}/motif2tf/motifs-v9-nr.mgi-m0.001-o0.0.tbl",
        size_gb=0.01,
        description="Motif-to-TF annotation for mouse (MGI symbols, v9 motif collection)",
    ),
    # TF lists
    DBEntry(
        alias="hg38_tfs",
        filename="allTFs_hg38.txt",
        url=f"{_BASE}/tf_lists/allTFs_hg38.txt",
        size_gb=0.001,
        description="Human TF list (~1800 TFs, HGNC symbols)",
    ),
    DBEntry(
        alias="mm10_tfs",
        filename="allTFs_mm.txt",
        url=f"{_BASE}/tf_lists/allTFs_mm.txt",
        size_gb=0.001,
        description="Mouse TF list (~1600 TFs, MGI symbols)",
    ),
]

_PRESETS: dict[str, list[str]] = {
    # Minimal — single database, enough to run pySCENIC ctx
    "human_minimal": [
        "hg38_refseq_10kb",
        "hg38_motifs",
        "hg38_tfs",
    ],
    "mouse_minimal": [
        "mm10_refseq_10kb",
        "mm10_motifs",
        "mm10_tfs",
    ],
    # Standard — two databases for better regulon coverage
    "human": [
        "hg38_refseq_500bp",
        "hg38_refseq_10kb",
        "hg38_motifs",
        "hg38_tfs",
    ],
    "mouse": [
        "mm10_refseq_500bp",
        "mm10_refseq_10kb",
        "mm10_motifs",
        "mm10_tfs",
    ],
    # Extended — refseq + SCREEN for distal enhancer coverage
    "human_with_screen": [
        "hg38_refseq_500bp",
        "hg38_refseq_10kb",
        "hg38_screen",
        "hg38_motifs",
        "hg38_tfs",
    ],
    "human_hg19": [
        "hg19_refseq_500bp",
        "hg19_refseq_10kb",
        "hg38_motifs",   # same motif annotation works for hg19
        "hg38_tfs",
    ],
}

_CATALOG_BY_ALIAS: dict[str, DBEntry] = {e.alias: e for e in _CATALOG}


def list_databases() -> None:
    """Print all available database aliases with descriptions and sizes."""
    print("\nAvailable pySCENIC database aliases:")
    print(f"{'Alias':<25} {'Size':>8}  Description")
    print("-" * 80)
    for entry in _CATALOG:
        size_str = f"{entry.size_gb:.0f} GB" if entry.size_gb >= 0.1 else f"{entry.size_gb*1000:.0f} MB"
        print(f"  {entry.alias:<23} {size_str:>8}  {entry.description}")

    print("\nAvailable presets:")
    for preset, aliases in _PRESETS.items():
        total_gb = sum(_CATALOG_BY_ALIAS[a].size_gb for a in aliases)
        print(f"  {preset:<25} ~{total_gb:.0f} GB  {', '.join(aliases)}")
    print()


def download(
    alias: str,
    dest_dir: str | Path = ".",
    skip_existing: bool = True,
) -> Path:
    """Download a single database file by alias.

    Args:
        alias: Database alias (see list_databases() for options).
        dest_dir: Destination directory (created if it doesn't exist).
        skip_existing: If True, skip download if the file already exists (default True).

    Returns:
        Path to the downloaded file.
    """
    if alias not in _CATALOG_BY_ALIAS:
        available = sorted(_CATALOG_BY_ALIAS.keys())
        raise ValueError(
            f"Unknown alias '{alias}'. Available: {available}"
        )

    entry = _CATALOG_BY_ALIAS[alias]
    dest_dir = Path(dest_dir).expanduser()
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / entry.filename

    if skip_existing and dest_path.exists():
        print(f"[skip] {entry.filename} already exists at {dest_path}")
        return dest_path

    size_str = f"{entry.size_gb:.0f} GB" if entry.size_gb >= 0.1 else f"{entry.size_gb*1000:.0f} MB"
    print(f"[download] {entry.filename} ({size_str})")
    print(f"           → {dest_path}")
    print(f"           from {entry.url}")

    _download_with_progress(entry.url, dest_path)
    return dest_path


def download_preset(
    preset: str,
    dest_dir: str | Path = ".",
    skip_existing: bool = True,
) -> dict[str, Path]:
    """Download all files in a preset.

    Args:
        preset: Preset name — one of: human, human_with_screen, human_hg19, mouse.
        dest_dir: Destination directory.
        skip_existing: Skip files that already exist.

    Returns:
        Dict mapping alias → downloaded file path.
    """
    if preset not in _PRESETS:
        raise ValueError(
            f"Unknown preset '{preset}'. Available: {sorted(_PRESETS.keys())}"
        )

    aliases = _PRESETS[preset]
    total_gb = sum(_CATALOG_BY_ALIAS[a].size_gb for a in aliases)
    print(f"\nPreset '{preset}': {len(aliases)} files, ~{total_gb:.0f} GB total")

    results: dict[str, Path] = {}
    for alias in aliases:
        results[alias] = download(alias, dest_dir=dest_dir, skip_existing=skip_existing)

    print(f"\nAll files for preset '{preset}' are in: {Path(dest_dir).expanduser()}")
    _print_config_snippet(results, dest_dir)
    return results


def _print_config_snippet(paths: dict[str, Path], dest_dir) -> None:
    """Print a ready-to-use config snippet for rna_grn_pyscenic."""
    dest = Path(dest_dir).expanduser()
    db_paths = [str(p) for alias, p in paths.items() if alias.endswith(("_refseq_10kb", "_refseq_500bp", "_screen"))]
    motif = next((str(p) for alias, p in paths.items() if "motifs" in alias), None)
    tfs = next((str(p) for alias, p in paths.items() if "_tfs" in alias), None)

    if db_paths:
        print("\nReady-to-use parameters for rna_grn_pyscenic:")
        print(f"  tf_list_path          = \"{tfs}\"")
        print(f"  cistarget_db_paths    = {db_paths}")
        print(f"  motif_annotations_path = \"{motif}\"")


def _download_with_progress(url: str, dest: Path) -> None:
    """Download url to dest with a simple progress display."""
    try:
        import urllib.request

        class _Progress:
            def __init__(self):
                self.last_pct = -1

            def __call__(self, block_num, block_size, total_size):
                if total_size <= 0:
                    return
                downloaded = block_num * block_size
                pct = min(100, int(downloaded * 100 / total_size))
                if pct != self.last_pct and pct % 5 == 0:
                    downloaded_gb = downloaded / 1e9
                    total_gb = total_size / 1e9
                    bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
                    print(f"\r  [{bar}] {pct:3d}%  {downloaded_gb:.2f}/{total_gb:.2f} GB", end="", flush=True)
                    self.last_pct = pct

        urllib.request.urlretrieve(url, dest, reporthook=_Progress())
        print()  # newline after progress bar

    except Exception as exc:
        if dest.exists():
            dest.unlink()  # remove partial file
        raise RuntimeError(f"Download failed: {exc}") from exc


# --- CLI entry point ---

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Download pySCENIC cisTarget databases, TF lists, and motif annotations."
    )
    parser.add_argument("--list", action="store_true", help="List all available databases and presets")
    parser.add_argument("--db", metavar="ALIAS", help="Download a single database by alias")
    parser.add_argument("--preset", metavar="PRESET", help="Download a full preset (human, human_with_screen, mouse, human_hg19)")
    parser.add_argument("--dest", metavar="DIR", default=".", help="Destination directory (default: current directory)")
    parser.add_argument("--force", action="store_true", help="Re-download even if file exists")

    args = parser.parse_args()

    if args.list:
        list_databases()
    elif args.db:
        download(args.db, dest_dir=args.dest, skip_existing=not args.force)
    elif args.preset:
        download_preset(args.preset, dest_dir=args.dest, skip_existing=not args.force)
    else:
        parser.print_help()
