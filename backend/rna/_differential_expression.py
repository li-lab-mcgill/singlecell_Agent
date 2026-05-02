"""RNA differential expression: wilcoxon, t-test, logreg, MAST, edgeR/DESeq2 pseudobulk."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Optional

from ..types import DEResult

KNOWN_METHODS = ("wilcoxon", "t", "logreg", "mast", "edger_pseudobulk", "deseq2_pseudobulk")


def dispatch(
    adata,
    *,
    group_key: str,
    method: str = "wilcoxon",
    runners=None,
    reference: str = "rest",
    output_dir: Optional[Path] = None,
    **kwargs: Any,
) -> DEResult:
    if group_key not in adata.obs:
        raise ValueError(f"group_key '{group_key}' not in adata.obs.")

    if method in ("wilcoxon", "t", "logreg"):
        return _run_scanpy(adata, group_key=group_key, method=method, reference=reference, output_dir=output_dir, **kwargs)
    if method == "mast":
        return _run_mast(adata, group_key=group_key, runners=runners, **kwargs)
    if method == "edger_pseudobulk":
        return _run_edger_pseudobulk(adata, group_key=group_key, runners=runners, **kwargs)
    if method == "deseq2_pseudobulk":
        return _run_deseq2_pseudobulk(adata, group_key=group_key, runners=runners, **kwargs)
    raise ValueError(f"Unknown rna.differential_expression method: {method}. Choose from {KNOWN_METHODS}.")


def _run_scanpy(
    adata,
    *,
    group_key: str,
    method: str,
    reference: str,
    output_dir: Optional[Path],
    top_n: int = 50,
    **_: Any,
) -> DEResult:
    import scanpy as sc

    method_map = {"wilcoxon": "wilcoxon", "t": "t-test", "logreg": "logreg"}
    sc.tl.rank_genes_groups(adata, groupby=group_key, method=method_map[method], reference=reference)
    rank = adata.uns["rank_genes_groups"]
    groups = list(rank["names"].dtype.names)
    top_per_group = {g: [str(x) for x in rank["names"][g][:top_n]] for g in groups}

    table_path: Optional[Path] = None
    if output_dir is not None:
        import pandas as pd

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        rows = []
        for g in groups:
            for i in range(len(rank["names"][g])):
                rows.append({
                    "group": g,
                    "rank": i + 1,
                    "gene": str(rank["names"][g][i]),
                    "score": float(rank["scores"][g][i]),
                    "pval": float(rank["pvals"][g][i]) if "pvals" in rank else None,
                    "pval_adj": float(rank["pvals_adj"][g][i]) if "pvals_adj" in rank else None,
                    "lfc": float(rank["logfoldchanges"][g][i]) if "logfoldchanges" in rank else None,
                })
        df = pd.DataFrame(rows)
        table_path = output_dir / f"de_{method}_{group_key}.parquet"
        df.to_parquet(table_path, index=False)

    return DEResult(
        method=method,
        group_key=group_key,
        n_groups=len(groups),
        n_genes=int(adata.n_vars),
        table_path=table_path,
        top_per_group=top_per_group,
    )


def _run_mast(adata, *, group_key, runners, **kwargs: Any) -> DEResult:
    return _run_r_differential_expression(
        adata,
        group_key=group_key,
        method="mast",
        runners=runners,
        script_name="rna/differential_expression_mast.R",
        **kwargs,
    )


def _run_edger_pseudobulk(adata, *, group_key, runners, **kwargs: Any) -> DEResult:
    return _run_r_differential_expression(
        adata,
        group_key=group_key,
        method="edger_pseudobulk",
        runners=runners,
        script_name="rna/differential_expression_edger_pseudobulk.R",
        require_sample_key=True,
        **kwargs,
    )


def _run_deseq2_pseudobulk(adata, *, group_key, runners, **kwargs: Any) -> DEResult:
    return _run_r_differential_expression(
        adata,
        group_key=group_key,
        method="deseq2_pseudobulk",
        runners=runners,
        script_name="rna/differential_expression_deseq2_pseudobulk.R",
        require_sample_key=True,
        **kwargs,
    )


def _run_r_differential_expression(
    adata,
    *,
    group_key: str,
    method: str,
    runners,
    script_name: str,
    reference: str = "rest",
    output_dir: Optional[Path] = None,
    top_n: int = 50,
    sample_key: Optional[str] = None,
    require_sample_key: bool = False,
    **kwargs: Any,
) -> DEResult:
    if runners is None or getattr(runners, "r", None) is None:
        raise RuntimeError(f"{method} requires the R runner. Pass runners=RunnerSuite(...).")

    inferred_sample_key = None
    if require_sample_key:
        inferred_sample_key = _resolve_sample_key(adata, sample_key)
    elif sample_key is not None:
        inferred_sample_key = sample_key

    with tempfile.NamedTemporaryFile(suffix=".mtx", delete=False) as tmp_matrix:
        input_matrix = Path(tmp_matrix.name)
    with tempfile.NamedTemporaryFile(suffix=".obs.csv", delete=False) as tmp_obs:
        input_obs = Path(tmp_obs.name)
    with tempfile.NamedTemporaryFile(suffix=".genes.txt", delete=False) as tmp_genes:
        input_genes = Path(tmp_genes.name)
    with tempfile.NamedTemporaryFile(suffix=".cells.txt", delete=False) as tmp_cells:
        input_cells = Path(tmp_cells.name)

    temp_output_dir: tempfile.TemporaryDirectory[str] | None = None
    if output_dir is None:
        temp_output_dir = tempfile.TemporaryDirectory(prefix=f"de_{method}_")
        output_base = Path(temp_output_dir.name)
        persisted_table_path: Optional[Path] = None
    else:
        output_base = Path(output_dir)
        output_base.mkdir(parents=True, exist_ok=True)
        persisted_table_path = output_base / f"de_{method}_{group_key}.csv"

    output_table_path = output_base / f"de_{method}_{group_key}.csv"
    try:
        _write_r_de_inputs(
            adata,
            matrix_path=input_matrix,
            obs_path=input_obs,
            genes_path=input_genes,
            cells_path=input_cells,
            method=method,
        )
        result_payload = runners.r.run_script(
            script_name,
            args={
                "input_matrix": str(input_matrix),
                "input_obs": str(input_obs),
                "input_genes": str(input_genes),
                "input_cells": str(input_cells),
                "output_table": str(output_table_path),
                "group_key": group_key,
                "reference": reference,
                "top_n": top_n,
                "sample_key": inferred_sample_key,
                **kwargs,
            },
            returns="json",
        )
        top_per_group = _extract_top_per_group(output_table_path, top_n=top_n)
        metrics = {
            key: value
            for key, value in dict(result_payload or {}).items()
            if key not in {"status", "method", "group_key", "output_table", "n_groups", "n_genes", "top_per_group"}
        }
        if inferred_sample_key is not None:
            metrics.setdefault("sample_key", inferred_sample_key)
        return DEResult(
            method=method,
            group_key=group_key,
            n_groups=int(result_payload.get("n_groups", len(top_per_group))),
            n_genes=int(result_payload.get("n_genes", adata.n_vars)),
            table_path=persisted_table_path,
            top_per_group=top_per_group,
            metrics=metrics,
        )
    finally:
        input_matrix.unlink(missing_ok=True)
        input_obs.unlink(missing_ok=True)
        input_genes.unlink(missing_ok=True)
        input_cells.unlink(missing_ok=True)
        if temp_output_dir is not None:
            temp_output_dir.cleanup()


def _write_r_de_inputs(
    adata,
    *,
    matrix_path: Path,
    obs_path: Path,
    genes_path: Path,
    cells_path: Path,
    method: str,
) -> None:
    from scipy.io import mmwrite

    from ._normalization import _select_count_matrix

    matrix, _source = _select_count_matrix(adata, method=method)
    mmwrite(matrix_path, matrix.T.tocsr())
    adata.obs.to_csv(obs_path)
    genes_path.write_text("\n".join(str(x) for x in adata.var_names) + "\n", encoding="utf-8")
    cells_path.write_text("\n".join(str(x) for x in adata.obs_names) + "\n", encoding="utf-8")


def _resolve_sample_key(adata, sample_key: Optional[str]) -> str:
    obs = getattr(adata, "obs", None)
    if obs is None:
        raise ValueError("Pseudobulk differential expression requires adata.obs.")

    columns = list(getattr(obs, "columns", []))
    if sample_key:
        if sample_key not in columns:
            raise ValueError(f"sample_key '{sample_key}' not found in adata.obs.")
        return sample_key

    for candidate in (
        "sample",
        "sample_id",
        "donor",
        "donor_id",
        "patient",
        "patient_id",
        "replicate",
        "replicate_id",
        "batch",
        "batch_id",
    ):
        if candidate in columns:
            return candidate
    raise ValueError(
        "Pseudobulk differential expression requires sample_key or one of the common replicate columns "
        "(sample, sample_id, donor, donor_id, patient, patient_id, replicate, replicate_id, batch, batch_id)."
    )


def _extract_top_per_group(table_path: Path, *, top_n: int) -> dict[str, list[str]]:
    import csv

    if not table_path.is_file():
        return {}
    with table_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    if not rows or "group" not in reader.fieldnames or "gene" not in reader.fieldnames:
        return {}

    def _numeric_or_inf(value: Any) -> float:
        if value in (None, ""):
            return float("inf")
        try:
            return float(value)
        except (TypeError, ValueError):
            return float("inf")

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        group_name = str(row.get("group", ""))
        grouped.setdefault(group_name, []).append(row)

    top_per_group: dict[str, list[str]] = {}
    for group_name, group_rows in grouped.items():
        ordered = sorted(
            group_rows,
            key=lambda row: (
                _numeric_or_inf(row.get("pval_adj")),
                _numeric_or_inf(row.get("pval")),
                _numeric_or_inf(row.get("rank")),
            ),
        )
        genes: list[str] = []
        for row in ordered:
            gene_str = str(row.get("gene", "")).strip()
            if gene_str and gene_str not in genes:
                genes.append(gene_str)
            if len(genes) >= top_n:
                break
        top_per_group[group_name] = genes
    return top_per_group
