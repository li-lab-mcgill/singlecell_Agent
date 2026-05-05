"""edgeR pseudobulk differential expression via Rscript subprocess."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from backend.types import DEResult

_R_SCRIPT = Path(__file__).parents[4] / "r_scripts" / "rna" / "differential_expression_edger_pseudobulk.R"


def run(
    adata,
    *,
    group_key: str,
    sample_key: str,
    reference: str = "rest",
    output_dir: Path | None = None,
    top_n: int = 50,
) -> DEResult:
    """Run edgeR pseudobulk differential expression.

    Requires at least 2 biological replicates (samples) per group.
    Calls the edgeR R script via subprocess — R + edgeR must be installed.

    Args:
        adata: AnnData with raw counts in adata.X or adata.layers["counts"].
        group_key: adata.obs column defining cell groups (e.g. "cell_type").
        sample_key: adata.obs column defining biological replicates (e.g. "donor_id").
                    Required for pseudobulk aggregation.
        reference: Reference group — "rest" (default) or a specific group name.
        output_dir: If provided, saves DE table as CSV here.
        top_n: Number of top genes per group to include in top_per_group.

    Returns:
        DEResult with edgeR results.
    """
    if group_key not in adata.obs:
        raise ValueError(f"group_key '{group_key}' not in adata.obs.")
    if sample_key not in adata.obs:
        raise ValueError(f"sample_key '{sample_key}' not in adata.obs.")

    _check_rscript()

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        h5ad_path = tmp / "input.h5ad"
        table_path = Path(output_dir) / "de_edger.csv" if output_dir else tmp / "de_edger.csv"

        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)

        adata.write_h5ad(h5ad_path)

        args = {
            "input_h5ad": str(h5ad_path),
            "output_table": str(table_path),
            "group_key": group_key,
            "sample_key": sample_key,
            "reference": reference,
        }
        args_json = tmp / "args.json"
        args_json.write_text(json.dumps(args))

        result = subprocess.run(
            ["Rscript", str(_R_SCRIPT), "--args-json", str(args_json)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"edgeR failed:\n{result.stderr}")

        return _parse_result(result.stdout, table_path, group_key, top_n)


def _parse_result(stdout: str, table_path: Path, group_key: str, top_n: int) -> DEResult:
    import pandas as pd

    meta = json.loads(stdout)
    df = pd.read_csv(table_path) if table_path.exists() else pd.DataFrame()

    groups = df["group"].unique().tolist() if "group" in df.columns else []
    top_per_group = {}
    for g in groups:
        genes = df[df["group"] == g].sort_values("pval_adj")["gene"].head(top_n).tolist()
        top_per_group[str(g)] = genes

    return DEResult(
        method="edger_pseudobulk",
        group_key=group_key,
        n_groups=meta.get("n_groups", len(groups)),
        n_genes=meta.get("n_genes", len(df)),
        table_path=table_path if table_path.exists() else None,
        top_per_group=top_per_group,
    )


def _check_rscript() -> None:
    result = subprocess.run(["Rscript", "--version"], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "Rscript not found on PATH. Install R from https://cran.r-project.org/\n"
            "Then install edgeR: BiocManager::install('edgeR')"
        )
