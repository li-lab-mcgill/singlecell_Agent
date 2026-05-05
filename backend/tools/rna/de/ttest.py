"""Student's t-test differential expression."""

from __future__ import annotations

from pathlib import Path
from backend.types import DEResult


def run(
    adata,
    *,
    group_key: str,
    reference: str = "rest",
    output_dir: Path | None = None,
    top_n: int = 50,
):
    from backend.tools.rna.de.wilcoxon import _run_scanpy_de
    return _run_scanpy_de(adata, group_key=group_key, method="t",
                          reference=reference, output_dir=output_dir, top_n=top_n)
