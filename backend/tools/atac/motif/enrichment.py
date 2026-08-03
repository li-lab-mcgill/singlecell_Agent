"""TF motif enrichment analysis on differential accessibility peaks.

Uses snap.tl.motif_enrichment() which computes group-level enrichment
of TF binding motifs in peaks. Returns per-group enrichment scores
stored in adata.uns["motif_enrichment"].

Requires a genome FASTA file for motif scanning.
"""

from __future__ import annotations

from pathlib import Path


def run(
    adata,
    *,
    group_key: str,
    genome_fasta_path: str | Path,
    motif_db: str = "JASPAR2024",
    organism: str = "human",
    test_method: str = "hypergeometric",
    output_dir: Path | None = None,
) -> object:
    """Run TF motif enrichment on differential accessibility peaks per group.

    Computes which TF binding motifs are enriched in the peaks of each cell
    group compared to background (all peaks). Results are group-level, not
    per-cell (for per-cell chromVAR-style scores, a separate tool is needed).

    Args:
        adata: AnnData with peak accessibility matrix. Peak names in
               adata.var_names must be in "chr:start-end" format.
               Requires adata.uns["rank_peaks_groups"] from atac_da_wilcoxon
               to define group-specific peak sets.
        group_key: adata.obs column defining groups (e.g. "leiden").
                   Used to build group-specific peak sets from DA results.
        genome_fasta_path: Path to genome FASTA file (bgzipped or plain).
                           Required for motif scanning.
        motif_db: JASPAR database version — "JASPAR2024" (default) or "JASPAR2022".
        organism: "human" or "mouse" (default "human").
        test_method: Enrichment test — "hypergeometric" (default) or "binomial".
        output_dir: If provided, saves enrichment tables as parquet per group.

    Returns:
        adata with adata.uns["motif_enrichment"]: dict of
        {group: DataFrame with motif enrichment results}.
    """
    import snapatac2 as snap
    import pandas as pd

    fasta = Path(genome_fasta_path)
    if not fasta.exists():
        raise FileNotFoundError(
            f"Genome FASTA not found: {fasta}\n"
            "Download from UCSC or Ensembl:\n"
            "  Human hg38: https://hgdownload.soe.ucsc.edu/goldenPath/hg38/bigZips/hg38.fa.gz\n"
            "  Mouse mm10: https://hgdownload.soe.ucsc.edu/goldenPath/mm10/bigZips/mm10.fa.gz"
        )

    # Build group → peak list mapping from DA results or cluster mean accessibility
    regions = _build_regions(adata, group_key)

    # Load motif database
    motifs = snap.tl.get_motifs(
        motif_db,
        organism="Homo sapiens" if organism == "human" else "Mus musculus",
    )

    # Run enrichment
    enrichment = snap.tl.motif_enrichment(
        motifs=motifs,
        regions=regions,
        genome_fasta=str(fasta),
        method=test_method,
    )
    # enrichment: dict of {group: DataFrame}

    adata.uns["motif_enrichment"] = {
        group: df.to_dict("records") for group, df in enrichment.items()
    }

    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        for group, df in enrichment.items():
            safe_name = str(group).replace("/", "_")
            df.to_parquet(output_dir / f"motif_enrichment_{safe_name}.parquet", index=False)

    return adata


def _build_regions(adata, group_key: str) -> dict[str, list[str]]:
    """Build {group: [peak_ids]} from DA results or top accessible peaks per group."""
    import numpy as np
    import scipy.sparse as sp

    # Prefer DA results if available
    if "rank_peaks_groups" in adata.uns:
        rank = adata.uns["rank_peaks_groups"]
        groups = list(rank["names"].dtype.names)
        return {g: [str(p) for p in rank["names"][g]] for g in groups}

    # Fall back: top 1000 most accessible peaks per cluster
    if group_key not in adata.obs:
        raise ValueError(
            f"group_key '{group_key}' not in adata.obs. "
            "Run atac_da_wilcoxon first to get DA peaks per group, or provide a valid group_key."
        )

    X = adata.X
    if sp.issparse(X):
        X = X.toarray()

    regions = {}
    for group in adata.obs[group_key].unique():
        mask = adata.obs[group_key] == group
        mean_acc = X[mask].mean(axis=0)
        top_idx = np.argsort(mean_acc)[-1000:][::-1]
        regions[str(group)] = [adata.var_names[i] for i in top_idx]

    return regions
