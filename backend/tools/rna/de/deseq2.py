"""DESeq2 pseudobulk differential expression via R runner."""

from __future__ import annotations

from pathlib import Path
from backend.types import DEResult


def run(
    adata,
    *,
    group_key: str,
    runners,
    sample_key: str | None = None,
    output_dir: Path | None = None,
    top_n: int = 50,
):
    from backend.rna._differential_expression import _run_r_differential_expression
    return _run_r_differential_expression(
        adata, group_key=group_key, method="deseq2_pseudobulk", runners=runners,
        script_name="rna/differential_expression_deseq2_pseudobulk.R",
        require_sample_key=True, sample_key=sample_key,
        output_dir=output_dir, top_n=top_n,
    )
