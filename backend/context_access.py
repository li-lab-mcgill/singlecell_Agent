from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


def read_dataset_summary(context: Any) -> Dict[str, Any]:
    summary = {
        "dataset_summary": str(getattr(context, "feat_stats", "") or "").strip(),
        "label_column": str(getattr(context, "label_column", "") or "").strip(),
    }
    try:
        dataset = context._load_any(context.data_mod1_path)
    except Exception as exc:
        summary["inspect_error"] = str(exc)
        return summary
    if dataset.get("type") != "h5ad":
        return summary
    adata = dataset["obj"]
    summary.update(_summarize_h5ad(adata))
    return summary


def _shape_of(value: Any) -> list[int] | None:
    shape = getattr(value, "shape", None)
    if not shape:
        return None
    try:
        return [int(item) for item in shape]
    except Exception:
        return None


def _summarize_h5ad(adata: Any) -> Dict[str, Any]:
    try:
        from scipy.sparse import issparse
    except Exception:
        def issparse(value: Any) -> bool:
            return hasattr(value, "toarray")

    obs_columns = [str(col) for col in getattr(getattr(adata, "obs", None), "columns", [])]
    var_columns = [str(col) for col in getattr(getattr(adata, "var", None), "columns", [])]
    obsm = getattr(adata, "obsm", {}) or {}
    varm = getattr(adata, "varm", {}) or {}
    layers = getattr(adata, "layers", {}) or {}
    uns = getattr(adata, "uns", {}) or {}
    x = getattr(adata, "X", None)
    cluster_or_annotation_columns = [
        col
        for col in obs_columns
        if any(token in col.lower() for token in ("cluster", "leiden", "louvain", "cell_type", "celltype", "annotation", "label"))
    ]
    return {
        "n_cells": int(getattr(adata, "n_obs", 0)),
        "n_genes": int(getattr(adata, "n_vars", 0)),
        "shape": [int(getattr(adata, "n_obs", 0)), int(getattr(adata, "n_vars", 0))],
        "x_dtype": str(getattr(x, "dtype", "unknown")),
        "x_is_sparse": bool(issparse(x)),
        "obs_columns": obs_columns,
        "var_columns": var_columns,
        "layers": {str(key): _shape_of(value) for key, value in layers.items()},
        "obsm": {str(key): _shape_of(value) for key, value in obsm.items()},
        "varm": {str(key): _shape_of(value) for key, value in varm.items()},
        "uns_keys": [str(key) for key in uns.keys()],
        "cluster_or_annotation_columns": cluster_or_annotation_columns,
    }


def read_label_distribution(context: Any, label_key: str) -> Dict[str, Any]:
    key = str(label_key or "").strip()
    if not key:
        raise ValueError("label_key must be non-empty")
    ds = context._load_any(context.data_mod1_path)
    if ds.get("type") != "h5ad":
        raise ValueError("label distribution is only supported for h5ad inputs")
    adata = ds["obj"]
    if key not in adata.obs.columns:
        raise ValueError(f"{key} not found in dataset obs columns")
    values = pd.Series(adata.obs[key]).astype(str)
    counts = Counter(v for v in values.tolist() if v and v.lower() != "nan")
    total = sum(counts.values())
    distribution = [
        {
            "label": label,
            "count": int(count),
            "fraction": float(count / total) if total else 0.0,
        }
        for label, count in counts.most_common()
    ]
    return {"label_key": key, "total": int(total), "distribution": distribution}


def read_prior_resource_summary(context: Any) -> Dict[str, Any]:
    try:
        payload = json.loads(str(getattr(context, "prior_resource_summary", "") or ""))
    except json.JSONDecodeError:
        payload = {}
    return payload if isinstance(payload, dict) else {}


def check_prior_coverage(context: Any, resource_name: str) -> Dict[str, Any]:
    resource = str(resource_name or "").strip().lower()
    summary = read_prior_resource_summary(context)
    resources = summary.get("prior_resources", [])
    resource_entry = None
    for item in resources:
        if not isinstance(item, dict):
            continue
        file_path = str(item.get("file_path", "")).lower()
        if resource and resource in file_path:
            resource_entry = item
            break

    if resource == "gene_embedding":
        gene_dir = Path(getattr(context, "dataset_dir", "")) / "gene_embedding"
        gene_names_path = gene_dir / "gene_names.txt"
        dataset = context._load_any(context.data_mod1_path)
        if dataset.get("type") == "h5ad" and gene_names_path.exists():
            adata = dataset["obj"]
            var_names = adata.var_names.tolist() if hasattr(adata.var_names, "tolist") else list(adata.var_names)
            dataset_genes = {str(g).strip().upper() for g in var_names}
            with open(gene_names_path, "r", encoding="utf-8") as f:
                embedded_genes = {line.strip().upper() for line in f if line.strip()}
            overlap = dataset_genes & embedded_genes
            return {
                "resource_name": "gene_embedding",
                "dataset_gene_count": int(len(dataset_genes)),
                "resource_gene_count": int(len(embedded_genes)),
                "matched_gene_count": int(len(overlap)),
                "coverage_fraction": float(len(overlap) / len(dataset_genes)) if dataset_genes else 0.0,
            }

    return {
        "resource_name": resource_name,
        "summary": resource_entry or {},
    }


def query_marker_database(context: Any, tissue: str, species: str) -> Dict[str, Any]:
    species_text = str(species or "").strip().lower()
    tissue_text = str(tissue or "").strip().lower()
    marker_path = Path(getattr(context, "dataset_dir", "")) / "Cell_marker_Human.xlsx"
    if not marker_path.exists():
        raise ValueError("Cell_marker_Human.xlsx not found")
    df = pd.read_excel(marker_path, sheet_name=0)
    filtered = df.copy()
    species_cols = [col for col in filtered.columns if "species" in str(col).lower()]
    tissue_cols = [col for col in filtered.columns if any(tok in str(col).lower() for tok in ["tissue", "organ", "source"])]
    cell_cols = [col for col in filtered.columns if "cell" in str(col).lower() and "marker" not in str(col).lower()]
    gene_cols = [col for col in filtered.columns if any(tok in str(col).lower() for tok in ["gene", "marker"])]

    if species_text and species_cols:
        mask = filtered[species_cols[0]].astype(str).str.lower().str.contains(species_text, na=False)
        filtered = filtered.loc[mask]
    if tissue_text and tissue_cols:
        mask = filtered[tissue_cols[0]].astype(str).str.lower().str.contains(tissue_text, na=False)
        if mask.any():
            filtered = filtered.loc[mask]

    cell_col = cell_cols[0] if cell_cols else None
    gene_col = gene_cols[-1] if gene_cols else None
    if cell_col is None or gene_col is None:
        return {"species": species, "tissue": tissue, "markers_by_cell_type": {}}

    markers_by_cell_type: Dict[str, List[str]] = {}
    for _, row in filtered.iterrows():
        cell_type = str(row.get(cell_col, "")).strip()
        if not cell_type:
            continue
        raw_genes = str(row.get(gene_col, "") or "")
        genes = [item.strip() for item in raw_genes.replace(";", ",").split(",") if item.strip()]
        if not genes:
            continue
        current = markers_by_cell_type.setdefault(cell_type, [])
        for gene in genes:
            if gene not in current:
                current.append(gene)
    top_items = dict(list(markers_by_cell_type.items())[:20])
    return {"species": species, "tissue": tissue, "markers_by_cell_type": top_items}


def query_pathway_database(context: Any, database: str, gene: str) -> Dict[str, Any]:
    gene_name = str(gene or "").strip().upper()
    db_name = str(database or "").strip().lower()
    dataset_dir = Path(getattr(context, "dataset_dir", ""))
    if db_name == "msigdb":
        path = dataset_dir / "MsigDB.csv"
    elif db_name == "go":
        path = dataset_dir / "GO_terms.csv"
    else:
        raise ValueError(f"Unsupported pathway database: {database}")
    if not path.exists():
        raise ValueError(f"Database file not found: {path}")

    df = pd.read_csv(path)
    matches: List[str] = []
    for _, row in df.iterrows():
        values = [str(value) for value in row.tolist()]
        haystack = ",".join(values).upper()
        if gene_name and gene_name in haystack:
            label = ""
            for key in ["gs_name", "term_name", "term", "set_name", "go_id"]:
                if key in df.columns:
                    label = str(row.get(key, "")).strip()
                    if label:
                        break
            if not label:
                label = values[0]
            if label and label not in matches:
                matches.append(label)
        if len(matches) >= 20:
            break
    return {"database": database, "gene": gene, "matches": matches}
