"""TF-region motif enrichment on topic region sets via pycistarget (SCENIC+ wrapper).

Runs cisTarget enrichment analysis on the topic region sets produced by
atac_topic_pycisTopic. Uses the run_pycistarget() wrapper from scenicplus, which
saves results to save_path/menr.pkl (the function returns None).

The menr.pkl path is stored in adata.uns for use by multi_grn_scenicplus.
"""

from __future__ import annotations

import logging
import os
import warnings
from pathlib import Path

logger = logging.getLogger(__name__)


def run(
    adata,
    *,
    species: str,
    ctx_db_path: str | Path,
    motif_annotations_path: str | Path,
    dem_db_path: str | Path | None = None,
    region_sets_key: str = "topic_region_sets",
    ctx_auc_threshold: float = 0.005,
    ctx_nes_threshold: float = 3.0,
    ctx_rank_threshold: float = 0.05,
    dem_log2fc_thr: float = 0.5,
    dem_motif_hit_thr: float = 3.0,
    dem_max_bg_regions: int = 500,
    annotation_version: str = "v9",
    n_cpu: int = 4,
    output_dir: Path | None = None,
) -> object:
    """Run pycistarget TF-region motif enrichment on topic region sets.

    Args:
        adata: AnnData. Must contain adata.uns[region_sets_key] produced by
               atac_topic_pycisTopic.
        species: Organism for TSS annotation download via biomart. One of:
                 'homo_sapiens', 'mus_musculus', 'drosophila_melanogaster',
                 'gallus_gallus'. Required — no default.
        ctx_db_path: Path to a cisTarget ranking .feather database file.
        motif_annotations_path: Path to motif-to-TF annotation file (.tbl).
        dem_db_path: Path to a DEM database. If None (default), DEM is disabled.
        region_sets_key: Key in adata.uns holding {topic: [peak_names]} dict
                         from atac_topic_pycisTopic (default 'topic_region_sets').
        ctx_auc_threshold: AUC threshold for cisTarget (default 0.005).
        ctx_nes_threshold: NES threshold for cisTarget (default 3.0).
        ctx_rank_threshold: Fraction of top-ranked regions (default 0.05 = top 5%).
        dem_log2fc_thr: Log2 fold-change threshold for DEM (default 0.5).
        dem_motif_hit_thr: Motif hit score threshold for DEM (default 3.0).
        dem_max_bg_regions: Max background regions for DEM sampling (default 500).
        annotation_version: cisTarget database version; must match the feather
                            database files (default 'v9'). Use 'v10nr_clust' for
                            v10nr_clust feather files.
        n_cpu: Number of parallel workers (default 4).
        output_dir: Directory for pycistarget intermediate files and menr pickle.
                    Required — menr.pkl is saved here.

    Returns:
        adata augmented in place with:
          - adata.uns["pycistarget_menr_path"]: path to menr.pkl saved by run_pycistarget
          - adata.uns["pycistarget_tf_region_links"]: merged TF-region summary DataFrame
    """
    assert region_sets_key in adata.uns, (
        f"adata.uns['{region_sets_key}'] not found. "
        "Run atac_topic_pycisTopic first to generate topic region sets."
    )
    assert adata.uns[region_sets_key], (
        f"adata.uns['{region_sets_key}'] is empty. "
        "Check that atac_topic_pycisTopic produced non-empty topic region sets."
    )
    if output_dir is None:
        raise ValueError(
            "output_dir is required for multi_grn_pycistarget — "
            "run_pycistarget saves menr.pkl to output_dir/pycistarget/menr.pkl."
        )

    return _run_pycistarget(
        adata,
        species=species,
        ctx_db_path=Path(ctx_db_path),
        motif_annotations_path=Path(motif_annotations_path),
        dem_db_path=Path(dem_db_path) if dem_db_path else None,
        region_sets_key=region_sets_key,
        ctx_auc_threshold=ctx_auc_threshold,
        ctx_nes_threshold=ctx_nes_threshold,
        ctx_rank_threshold=ctx_rank_threshold,
        dem_log2fc_thr=dem_log2fc_thr,
        dem_motif_hit_thr=dem_motif_hit_thr,
        dem_max_bg_regions=dem_max_bg_regions,
        annotation_version=annotation_version,
        n_cpu=n_cpu,
        output_dir=Path(output_dir),
    )


def _peaks_to_pyranges(peak_names: list[str]):
    """Convert 'chr:start-end' peak strings to a PyRanges object."""
    import pyranges as pr

    parts = [p.replace(":", "-").split("-") for p in peak_names]
    return pr.PyRanges(
        chromosomes=[p[0] for p in parts],
        starts=[int(p[1]) for p in parts],
        ends=[int(p[2]) for p in parts],
    )


def _run_pycistarget(
    adata,
    *,
    species,
    ctx_db_path,
    motif_annotations_path,
    dem_db_path,
    region_sets_key,
    ctx_auc_threshold,
    ctx_nes_threshold,
    ctx_rank_threshold,
    dem_log2fc_thr,
    dem_motif_hit_thr,
    dem_max_bg_regions,
    annotation_version,
    n_cpu,
    output_dir,
):
    import dill
    import pandas as pd
    from scenicplus.wrappers.run_pycistarget import run_pycistarget

    output_dir.mkdir(parents=True, exist_ok=True)
    save_path = str(output_dir / "pycistarget")

    # Convert peak name strings → PyRanges objects required by run_pycistarget
    raw_region_sets = adata.uns[region_sets_key]
    region_sets = {
        k: _peaks_to_pyranges(v)
        for k, v in raw_region_sets.items()
    }
    logger.info("Running pycistarget on %d topic region sets", len(region_sets))

    # run_pycistarget returns None — it saves menr.pkl to save_path/menr.pkl
    run_pycistarget(
        region_sets=region_sets,
        species=species,
        save_path=save_path,
        ctx_db_path=str(ctx_db_path),
        dem_db_path=str(dem_db_path) if dem_db_path else None,
        path_to_motif_annotations=str(motif_annotations_path),
        annotation_version=annotation_version,
        ctx_auc_threshold=ctx_auc_threshold,
        ctx_nes_threshold=ctx_nes_threshold,
        ctx_rank_threshold=ctx_rank_threshold,
        dem_log2fc_thr=dem_log2fc_thr,
        dem_motif_hit_thr=dem_motif_hit_thr,
        dem_max_bg_regions=dem_max_bg_regions,
        n_cpu=n_cpu,
    )

    # Load the menr dict that run_pycistarget saved to disk
    menr_pkl_path = Path(save_path) / "menr.pkl"
    assert menr_pkl_path.exists(), (
        f"run_pycistarget did not produce {menr_pkl_path}. "
        "Check that pycistarget ran without error."
    )
    with open(menr_pkl_path, "rb") as f:
        menr = dill.load(f)

    adata.uns["pycistarget_menr_path"] = str(menr_pkl_path)
    logger.info("menr dict loaded from %s", menr_pkl_path)

    # Extract summary: merge TF-region enrichment entries across all topics
    tf_region_frames = []
    for outer_key, annotation_dict in menr.items():
        if isinstance(annotation_dict, dict):
            for annot_name, result in annotation_dict.items():
                if hasattr(result, "motif_enrichment"):
                    df = result.motif_enrichment.copy()
                    df["menr_key"] = outer_key
                    df["annotation"] = annot_name
                    tf_region_frames.append(df)
    if tf_region_frames:
        adata.uns["pycistarget_tf_region_links"] = pd.concat(
            tf_region_frames, ignore_index=True
        )
        logger.info(
            "pycistarget complete: %d TF-region enrichment entries across %d topics",
            len(adata.uns["pycistarget_tf_region_links"]),
            len(region_sets),
        )
    else:
        logger.warning("pycistarget produced no enrichment entries.")

    return adata
