"""TF activity scoring via decoupler-py + CollecTRI prior knowledge network.

Runs ULM (Univariate Linear Model) to estimate TF activity scores for each cell.
Results are stored in adata.obsm["ulm_estimate"] and adata.obsm["ulm_pvals"].
"""

from __future__ import annotations

from pathlib import Path

from backend.types import GRN


def run(
    adata,
    *,
    network: str = "collectri",
    organism: str = "human",
    min_n: int = 5,
    output_dir: Path | None = None,
) -> GRN:
    """Score TF activity using decoupler ULM with a prior knowledge network.

    Args:
        adata: AnnData with normalized log1p counts in adata.X.
        network: Prior knowledge network — "collectri" (default) or "dorothea".
        organism: "human" or "mouse".
        min_n: Minimum number of targets a TF must have to be scored.
        output_dir: If provided, saves the TF activity table as a parquet file.

    Returns:
        GRN result with TF activity stored in adata.obsm.
    """
    return _run_decoupler(
        adata,
        network=network,
        organism=organism,
        min_n=min_n,
        output_dir=output_dir,
    )


def _run_decoupler(adata, *, network, organism, min_n, output_dir) -> GRN:
    import decoupler as dc

    # Load prior knowledge network
    if network == "collectri":
        net = dc.get_collectri(organism=organism, split_complexes=False)
        net_label = "CollecTRI"
    elif network == "dorothea":
        net = dc.get_dorothea(organism=organism)
        # Keep only high-confidence interactions
        net = net[net["confidence"].isin(["A", "B", "C"])]
        net_label = "DoRothEA (A-C)"
    else:
        raise ValueError(f"Unknown network '{network}'. Choose 'collectri' or 'dorothea'.")

    # Run ULM
    dc.run_ulm(
        mat=adata,
        net=net,
        source="source",
        target="target",
        weight="weight",
        verbose=False,
        min_n=min_n,
        use_raw=False,
    )
    # Results land in adata.obsm["ulm_estimate"] and adata.obsm["ulm_pvals"]

    acts = adata.obsm.get("ulm_estimate")
    n_tfs = int(acts.shape[1]) if acts is not None else 0

    # Collect all TF → target edges from the filtered network for counting
    tfs_scored = set(acts.columns.tolist()) if acts is not None else set()
    net_filtered = net[net["source"].isin(tfs_scored)]
    n_targets = int(net_filtered["target"].nunique())
    n_edges = int(len(net_filtered))

    table_path = None
    if output_dir is not None and acts is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        table_path = output_dir / f"grn_decoupler_{network}.parquet"
        acts.to_parquet(table_path)

    return GRN(
        method=f"decoupler_ulm_{network}",
        n_tfs=n_tfs,
        n_targets=n_targets,
        n_edges=n_edges,
        edges_path=table_path,
        metadata={
            "network": net_label,
            "organism": organism,
            "min_n": min_n,
            "activity_key": "ulm_estimate",
            "pvals_key": "ulm_pvals",
        },
    )
