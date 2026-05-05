"""ATAC fragment size distribution and TSS enrichment QC.

Uses snapatac2 metrics to compute per-cell QC scores from fragment data.
"""

from __future__ import annotations

from pathlib import Path


def run(
    adata,
    *,
    gtf_path: str | Path | None = None,
    exclude_chroms: list[str] | None = None,
) -> object:
    """Compute fragment size QC metrics and add to adata.obs/uns.

    Computes:
    - Fragment size distribution (stored in adata.uns["frag_size_distr"])
    - TSS enrichment score per cell in adata.obs["tsse"] (requires gtf_path)

    Args:
        adata: AnnData (snapatac2 format with fragment data loaded).
               Fragment data must have been loaded during import via
               snap.pp.import_data() — it is embedded in the adata object.
        gtf_path: Path to genome GTF/GFF file for TSS enrichment computation.
                  If None, TSS enrichment is skipped.
        exclude_chroms: Chromosomes to exclude from TSS enrichment computation.
                        Defaults to ["chrM", "M"].

    Returns:
        adata with QC metrics added.
    """
    import snapatac2 as snap

    if exclude_chroms is None:
        exclude_chroms = ["chrM", "M"]

    # Fragment size distribution — stored in adata.uns
    snap.metrics.frag_size_distr(adata, add_key="frag_size_distr", inplace=True)

    # TSS enrichment score — stored in adata.obs["tsse"]
    if gtf_path is not None:
        gtf = Path(gtf_path)
        if not gtf.exists():
            raise FileNotFoundError(
                f"GTF file not found: {gtf}\n"
                "Download from GENCODE: https://www.gencodegenes.org/human/\n"
                "  e.g. gencode.v44.annotation.gtf.gz (human hg38)"
            )
        snap.metrics.tsse(
            adata,
            gene_anno=str(gtf),
            exclude_chroms=exclude_chroms,
            inplace=True,
        )

    return adata
