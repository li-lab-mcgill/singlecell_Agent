"""Full pySCENIC pipeline: GRNBoost2 co-expression + cisTarget motif pruning → regulons.

Runs both stages in sequence:
  1. GRNBoost2 (arboreto): expression → TF→gene importance scores
  2. pySCENIC ctx: prune using TF motif binding databases → validated regulons

Supports both refseq and SCREEN cisTarget databases.
Accepts one or more .feather database files (multiple databases improve coverage).

If you only want the co-expression adjacency matrix, use rna_grn_grnboost2 instead.

Requires cisTarget database files (large, downloaded separately from pySCENIC resources).
"""

from __future__ import annotations

from pathlib import Path

from backend.types import GRN


def run(
    adata,
    *,
    tf_list_path: str | Path,
    cistarget_db_paths: list[str | Path] | str | Path,
    motif_annotations_path: str | Path,
    output_dir: Path | None = None,
    n_jobs: int = 4,
    seed: int = 42,
    rank_threshold: int = 1500,
    auc_threshold: float = 0.05,
    nes_threshold: float = 3.0,
) -> GRN:
    """Run pySCENIC: GRNBoost2 co-expression + cisTarget motif pruning.

    Args:
        adata: AnnData with normalized log1p counts in adata.X.
        tf_list_path: Path to TF list file (one TF symbol per line, e.g. allTFs_hg38.txt).
        cistarget_db_paths: One or more .feather cisTarget ranking database paths.
            Accepts a single path or a list of paths. Using two databases (e.g. 500bp + 10kb
            refseq, or refseq + SCREEN) gives better regulon coverage than a single database.
            All databases must use the same genome assembly and the same motif annotation file.
        motif_annotations_path: Path to motif-to-TF annotation TSV. Must match the genome
            and motif collection of the cisTarget databases.
        output_dir: Directory for intermediate files and final outputs.
        n_jobs: GRNBoost2 parallel workers (default 4).
        seed: GRNBoost2 random seed (default 42).
        rank_threshold: cisTarget rank cutoff — genes ranked above this are considered
            targets; 1500 is standard for 10kb databases (default 1500).
        auc_threshold: AUC cutoff for regulon inclusion (default 0.05).
        nes_threshold: Normalized enrichment score cutoff for motif enrichment (default 3.0).

    Returns:
        GRN result. Regulons stored in adata.uns["pyscenic_regulons"].
    """
    # Normalize cistarget_db_paths to a list of Path objects
    if isinstance(cistarget_db_paths, (str, Path)):
        db_paths = [Path(cistarget_db_paths)]
    else:
        db_paths = [Path(p) for p in cistarget_db_paths]

    return _run_pyscenic(
        adata,
        tf_list_path=Path(tf_list_path),
        db_paths=db_paths,
        motif_annotations_path=Path(motif_annotations_path),
        output_dir=Path(output_dir) if output_dir else None,
        n_jobs=n_jobs,
        seed=seed,
        rank_threshold=rank_threshold,
        auc_threshold=auc_threshold,
        nes_threshold=nes_threshold,
    )


def _check_required_files(tf_list_path, db_paths, motif_annotations_path) -> None:
    """Raise a clear, actionable error if any required database file is missing."""
    missing = []
    for p in [tf_list_path, motif_annotations_path, *db_paths]:
        if not p.exists():
            missing.append(str(p))

    if missing:
        missing_str = "\n".join(f"  - {p}" for p in missing)
        raise FileNotFoundError(
            f"pySCENIC requires external database files that were not found:\n{missing_str}\n\n"
            "Download them with:\n"
            "  from backend.tools.rna.grn.download_databases import download_preset, list_databases\n\n"
            "  # See what's available\n"
            "  list_databases()\n\n"
            "  # Download all files for human hg38\n"
            "  download_preset('human', dest_dir='~/pyscenic_data')\n\n"
            "  # Or with SCREEN databases for distal enhancers\n"
            "  download_preset('human_with_screen', dest_dir='~/pyscenic_data')\n\n"
            "Or from the CLI:\n"
            "  python -m backend.tools.rna.grn.download_databases --preset human --dest ~/pyscenic_data\n\n"
            "See wiki resource node: resources/pyscenic_databases"
        )


def _run_pyscenic(
    adata,
    *,
    tf_list_path,
    db_paths,
    motif_annotations_path,
    output_dir,
    n_jobs,
    seed,
    rank_threshold,
    auc_threshold,
    nes_threshold,
) -> GRN:
    import pandas as pd
    import scipy.sparse as sp
    from arboreto.algo import grnboost2
    from arboreto.utils import load_tf_names
    from pyscenic.ctx import df2regulons, load_motif_annotations
    from ctxcore.rnkdb import FeatherRankingDatabase

    # --- Pre-flight: verify all required files exist before starting ---
    _check_required_files(tf_list_path, db_paths, motif_annotations_path)

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

    # --- Stage 1: GRNBoost2 ---
    X = adata.X
    if sp.issparse(X):
        X = X.toarray()
    expr_df = pd.DataFrame(X, index=adata.obs_names, columns=adata.var_names)

    tf_names = load_tf_names(str(tf_list_path))
    tf_names = [t for t in tf_names if t in adata.var_names]
    if not tf_names:
        raise ValueError(
            f"None of the TFs in '{tf_list_path}' were found in adata.var_names."
        )

    adjacencies = grnboost2(
        expression_data=expr_df,
        tf_names=tf_names,
        verbose=False,
        seed=seed,
    )

    adj_path = None
    if output_dir is not None:
        adj_path = output_dir / "adjacencies.parquet"
        adjacencies.to_parquet(adj_path, index=False)

    # --- Stage 2: cisTarget motif pruning ---
    dbs = [
        FeatherRankingDatabase(fname=str(p), name=p.stem)
        for p in db_paths
    ]
    motif_annotations = load_motif_annotations(str(motif_annotations_path))

    regulons = df2regulons(
        adjacencies,
        dbs=dbs,
        motif_annotations=motif_annotations,
        rank_threshold=rank_threshold,
        auc_threshold=auc_threshold,
        nes_threshold=nes_threshold,
    )

    # Store regulons in adata
    adata.uns["pyscenic_regulons"] = {
        r.name: list(r.gene2weight.keys()) for r in regulons
    }

    regulon_path = None
    if output_dir is not None:
        import json
        regulon_path = output_dir / "regulons.json"
        with open(regulon_path, "w") as f:
            json.dump(adata.uns["pyscenic_regulons"], f, indent=2)

    n_tfs = int(adjacencies["TF"].nunique())
    n_targets = int(adjacencies["target"].nunique())
    n_edges = len(adjacencies)

    return GRN(
        method="pyscenic",
        n_tfs=n_tfs,
        n_targets=n_targets,
        n_edges=n_edges,
        edges_path=adj_path,
        metadata={
            "n_regulons": len(regulons),
            "databases": [p.name for p in db_paths],
            "rank_threshold": rank_threshold,
            "auc_threshold": auc_threshold,
            "nes_threshold": nes_threshold,
            "regulons_key": "pyscenic_regulons",
            "regulon_path": str(regulon_path) if regulon_path else None,
        },
    )
