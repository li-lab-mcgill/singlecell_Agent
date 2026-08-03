"""DESeq2 pseudobulk differential expression via Rscript subprocess."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from backend.types import DEResult

_R_SCRIPT = Path(__file__).parents[3] / "r_scripts" / "rna" / "differential_expression_deseq2_pseudobulk.R"


def run(
    adata,
    *,
    group_key: str,
    sample_key: str | None = None,
    output_dir: Path | None = None,
    top_n: int = 50,
) -> DEResult:
    """Run DESeq2 pseudobulk differential expression.

    Requires at least 2 biological replicates (samples) per group.
    Calls the DESeq2 R script via subprocess — R + DESeq2 must be installed
    (auto-installed via BiocManager if missing).

    Args:
        adata:     AnnData with raw counts in adata.X or adata.layers["counts"].
        group_key: adata.obs column defining cell groups (e.g. "cell_type").
        sample_key: adata.obs column defining biological replicates (e.g. "donor_id").
                    Required for pseudobulk aggregation.
        output_dir: If provided, saves DE table as CSV here.
        top_n:     Number of top genes per group to include in top_per_group.

    Returns:
        DEResult with DESeq2 results.
    """
    if group_key not in adata.obs:
        raise ValueError(f"group_key '{group_key}' not in adata.obs.")
    if sample_key and sample_key not in adata.obs:
        raise ValueError(f"sample_key '{sample_key}' not in adata.obs.")

    _check_rscript()

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        h5ad_path = tmp / "input.h5ad"
        table_path = Path(output_dir) / "de_deseq2.csv" if output_dir else tmp / "de_deseq2.csv"

        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)

        adata.write_h5ad(h5ad_path)

        args = {
            "input_h5ad": str(h5ad_path),
            "output_table": str(table_path),
            "group_key": group_key,
            "sample_key": sample_key or "",
            "reference": "rest",
        }
        args_json = tmp / "args.json"
        args_json.write_text(json.dumps(args))

        env = {**os.environ, "KMP_DUPLICATE_LIB_OK": "TRUE", "OMP_NUM_THREADS": "1"}
        result = subprocess.run(
            ["Rscript", "--no-init-file", str(_R_SCRIPT), "--args-json", str(args_json)],
            capture_output=True, text=True, env=env,
        )
        if result.returncode != 0:
            raise RuntimeError(f"DESeq2 failed:\n{result.stderr}")

        return _parse_result(result.stdout, table_path, group_key, top_n)


def _parse_result(stdout: str, table_path: Path, group_key: str, top_n: int) -> DEResult:
    import pandas as pd

    meta = json.loads(stdout) if stdout.strip() else {}
    df = pd.read_csv(table_path) if table_path.exists() else pd.DataFrame()

    groups = df["group"].unique().tolist() if "group" in df.columns else []
    top_per_group = {}
    for g in groups:
        genes = df[df["group"] == g].sort_values("pval_adj")["gene"].head(top_n).tolist()
        top_per_group[str(g)] = genes

    return DEResult(
        method="deseq2_pseudobulk",
        group_key=group_key,
        n_groups=meta.get("n_groups", len(groups)),
        n_genes=meta.get("n_genes", len(df)),
        table_path=table_path if table_path.exists() else None,
        top_per_group=top_per_group,
    )


def _check_rscript() -> None:
    result = subprocess.run(["Rscript", "--version"], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("Rscript not found on PATH. Install R from https://cran.r-project.org/")
    _ensure_r_packages(["BiocManager"], bioc=False)
    _ensure_r_packages(["DESeq2"], bioc=True)


def _ensure_r_packages(packages: list[str], *, bioc: bool) -> None:
    missing_r = "c(" + ", ".join(f'"{p}"' for p in packages) + ")"
    check = f'missing <- {missing_r}[!sapply({missing_r}, requireNamespace, quietly=TRUE)]; cat(paste(missing, collapse=","))'
    res = subprocess.run(["Rscript", "--no-init-file", "-e", check], capture_output=True, text=True, timeout=30)
    missing = [p.strip() for p in res.stdout.strip().split(",") if p.strip()]
    if not missing:
        return
    missing_r2 = "c(" + ", ".join(f'"{p}"' for p in missing) + ")"
    if bioc:
        install_cmd = f'BiocManager::install({missing_r2}, ask=FALSE, update=FALSE)'
    else:
        install_cmd = f'install.packages({missing_r2}, repos="https://cloud.r-project.org")'
    res2 = subprocess.run(["Rscript", "--no-init-file", "-e", install_cmd], capture_output=True, text=True, timeout=600)
    if res2.returncode != 0:
        raise RuntimeError(f"Failed to install R packages {missing}:\n{res2.stderr}")
