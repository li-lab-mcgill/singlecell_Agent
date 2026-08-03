"""Peak-to-gene correlation using SCENIC+ search space and importance scoring.

Computes region → gene regulatory links by:
  1. Defining a genomic search space (peaks within ±150kb of TSS by default)
  2. Scoring each candidate peak-gene pair with random forest importance
     (GBM, RF, or ET) and Spearman correlation

Output is a filtered DataFrame stored in adata.uns["scenicplus_peak_gene_links"].
This is the required input for multi_grn_scenicplus.

This tool is separate from atac_peak_to_gene_correlation, which uses Pearson
correlation, a 500kb window, and a different output schema.
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path

logger = logging.getLogger(__name__)


_SPECIES_DATASET = {
    "homo_sapiens": "hsapiens_gene_ensembl",
    "mus_musculus": "mmusculus_gene_ensembl",
    "drosophila_melanogaster": "dmelanogaster_gene_ensembl",
    "gallus_gallus": "ggallus_gene_ensembl",
}


def run(
    adata,
    *,
    rna_h5ad_path: str | Path,
    species: str = "homo_sapiens",
    gene_annotation=None,
    chromsizes=None,
    search_space_upstream: tuple[int, int] = (1_000, 150_000),
    search_space_downstream: tuple[int, int] = (1_000, 150_000),
    search_space_extend_tss: tuple[int, int] = (10, 10),
    importance_threshold: float = 0.05,
    rho_threshold: float = 0.03,
    importance_scoring_method: str = "GBM",
    n_cpu: int = 4,
    annotation_source: str = "biomart",
    biomart_host: str | None = None,
    gtf_path: str | Path | None = None,
    chromsizes_path: str | Path | None = None,
    output_dir: Path | None = None,
) -> object:
    """Compute SCENIC+-style peak-to-gene regulatory links.

    Args:
        adata: AnnData (ATAC). Peak names in adata.var_names must be 'chr:start-end'.
               adata.X should be accessible (not necessarily raw; used for correlation).
        rna_h5ad_path: Path to the paired RNA AnnData (.h5ad). Cells must overlap
                       with adata.obs_names (multi-ome barcodes).
        species: Organism for biomart gene annotation and chromosome sizes fetch.
                 One of 'homo_sapiens' (default), 'mus_musculus',
                 'drosophila_melanogaster', 'gallus_gallus'. Ignored when
                 gene_annotation and chromsizes are both provided explicitly, or
                 when annotation_source='gtf'.
        gene_annotation: DataFrame with columns Chromosome, Start, Strand, Gene.
                         If None, fetched from biomart (requires internet).
        chromsizes: DataFrame with columns Chromosome and End (chromosome length).
                    If None, fetched from biomart or loaded from chromsizes_path.
        search_space_upstream: (min_bp, max_bp) upstream of TSS (default (1000, 150000)).
        search_space_downstream: (min_bp, max_bp) downstream of TSS (default (1000, 150000)).
        search_space_extend_tss: (upstream_ext, downstream_ext) TSS extension
                                  (default (10, 10)).
        importance_threshold: Post-hoc filter — discard links with importance below
                              this value (default 0.05). Not a parameter of the
                              scoring function.
        rho_threshold: Post-hoc filter — discard links where |Spearman rho| is below
                       this value (default 0.03). Links with rho > 0 are activating,
                       rho < 0 are repressing.
        importance_scoring_method: Random forest algorithm for importance scoring.
                                   'GBM' (gradient boosted, default), 'RF' (random
                                   forest), or 'ET' (extra trees).
        n_cpu: Number of parallel workers (default 4).
        annotation_source: 'biomart' (default) or 'gtf'. Use 'gtf' for offline.
        biomart_host: Optional biomart host URL. Uses default if None.
        gtf_path: Path to GTF file for offline gene annotation (used when
                  annotation_source='gtf').
        chromsizes_path: Path to UCSC .chrom.sizes file. Alternative to biomart
                         for offline chromsizes.
        output_dir: Directory for temporary scoring files.

    Returns:
        adata augmented in place with:
          - adata.uns["scenicplus_peak_gene_links"]: filtered DataFrame with columns
            [region, target, importance, rho, Distance]
    """
    if adata.n_obs < 200:
        warnings.warn(
            f"Only {adata.n_obs} cells present. Peak-to-gene correlation requires "
            "at least 200 cells for stable estimates. Consider pseudobulk aggregation "
            "before running this tool.",
            UserWarning,
            stacklevel=2,
        )

    if species not in _SPECIES_DATASET:
        raise ValueError(
            f"species='{species}' is not supported. "
            f"Valid values: {list(_SPECIES_DATASET.keys())}"
        )

    return _run_peak_to_gene(
        adata,
        rna_h5ad_path=Path(rna_h5ad_path),
        species=species,
        gene_annotation=gene_annotation,
        chromsizes=chromsizes,
        search_space_upstream=search_space_upstream,
        search_space_downstream=search_space_downstream,
        search_space_extend_tss=search_space_extend_tss,
        importance_threshold=importance_threshold,
        rho_threshold=rho_threshold,
        importance_scoring_method=importance_scoring_method,
        n_cpu=n_cpu,
        annotation_source=annotation_source,
        biomart_host=biomart_host,
        gtf_path=Path(gtf_path) if gtf_path else None,
        chromsizes_path=Path(chromsizes_path) if chromsizes_path else None,
        output_dir=Path(output_dir) if output_dir else None,
    )


def _fetch_gene_annotation(species: str, biomart_host: str | None):
    """Fetch TSS annotation DataFrame from biomart."""
    import pybiomart as pbm
    import pandas as pd

    host = biomart_host or "http://www.ensembl.org"
    server = pbm.Server(host=host, use_cache=False)
    mart = server["ENSEMBL_MART_ENSEMBL"]

    dataset_name = _SPECIES_DATASET.get(species, "hsapiens_gene_ensembl")
    logger.info("Fetching gene annotation from biomart dataset '%s'", dataset_name)
    dataset = mart[dataset_name]
    result = dataset.query(
        attributes=["chromosome_name", "transcription_start_site", "strand", "external_gene_name"],
        filters={"biotype": "protein_coding"},
    )
    result.columns = ["Chromosome", "Start", "Strand", "Gene"]
    result["Chromosome"] = "chr" + result["Chromosome"].astype(str)
    result = result[result["Chromosome"].str.match(r"^chr\d+$|^chrX$|^chrY$")]
    return result


def _fetch_chromsizes_biomart(species: str, biomart_host: str | None):
    """Fetch chromosome sizes as DataFrame with Chromosome and End columns."""
    import pybiomart as pbm
    import pandas as pd

    host = biomart_host or "http://www.ensembl.org"
    server = pbm.Server(host=host, use_cache=False)
    mart = server["ENSEMBL_MART_ENSEMBL"]
    dataset_name = _SPECIES_DATASET.get(species, "hsapiens_gene_ensembl")
    logger.info("Fetching chromsizes from biomart dataset '%s'", dataset_name)
    dataset = mart[dataset_name]
    result = dataset.query(
        attributes=["chromosome_name", "chromosome_length"],
    )
    result.columns = ["Chromosome", "End"]
    result["Start"] = 0
    result["Chromosome"] = "chr" + result["Chromosome"].astype(str)
    result = result[result["Chromosome"].str.match(r"^chr\d+$|^chrX$|^chrY$")]
    result = result.drop_duplicates("Chromosome")
    return result[["Chromosome", "Start", "End"]]


def _load_chromsizes_file(path: Path):
    """Load UCSC .chrom.sizes file into DataFrame with Chromosome and End columns."""
    import pandas as pd

    df = pd.read_csv(path, sep="\t", header=None, names=["Chromosome", "End"])
    df["Start"] = 0
    return df[["Chromosome", "Start", "End"]]


def _run_peak_to_gene(
    adata,
    *,
    rna_h5ad_path,
    species,
    gene_annotation,
    chromsizes,
    search_space_upstream,
    search_space_downstream,
    search_space_extend_tss,
    importance_threshold,
    rho_threshold,
    importance_scoring_method,
    n_cpu,
    annotation_source,
    biomart_host,
    gtf_path,
    chromsizes_path,
    output_dir,
):
    import pandas as pd
    import scipy.sparse as sp
    import scanpy as sc
    from scenicplus.data_wrangling.gene_search_space import get_search_space
    from scenicplus.enhancer_to_gene import calculate_regions_to_genes_relationships

    import tempfile
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        r2g_tmp = output_dir / "r2g_tmp"
        r2g_tmp.mkdir(parents=True, exist_ok=True)
    else:
        # Use a unique temp dir to avoid collision when multiple runs execute concurrently
        r2g_tmp = Path(tempfile.mkdtemp(prefix="r2g_tmp_"))

    rna_adata = sc.read_h5ad(rna_h5ad_path)

    # --- Gene annotation ---
    if gene_annotation is None:
        if annotation_source == "gtf" and gtf_path is not None:
            logger.info("Loading gene annotation from GTF: %s", gtf_path)
            gene_annotation = _parse_gtf_annotation(gtf_path)
        else:
            gene_annotation = _fetch_gene_annotation(species, biomart_host)

    # --- Chromosome sizes ---
    if chromsizes is None:
        if chromsizes_path is not None:
            chromsizes = _load_chromsizes_file(chromsizes_path)
        else:
            chromsizes = _fetch_chromsizes_biomart(species, biomart_host)

    # --- Step 1: define search space ---
    logger.info("Defining peak-gene search space (upstream=%s, downstream=%s)", search_space_upstream, search_space_downstream)
    search_space_df = get_search_space(
        scplus_region=set(adata.var_names),
        scplus_genes=set(rna_adata.var_names),
        gene_annotation=gene_annotation,
        chromsizes=chromsizes,
        upstream=search_space_upstream,
        downstream=search_space_downstream,
        extend_tss=search_space_extend_tss,
    )
    logger.info("Search space: %d candidate peak-gene pairs", len(search_space_df))

    # --- Step 2: importance scoring + Spearman correlation ---
    df_acc = pd.DataFrame(
        adata.X.toarray() if sp.issparse(adata.X) else adata.X,
        index=adata.obs_names,
        columns=adata.var_names,
    )
    df_exp = pd.DataFrame(
        rna_adata.X.toarray() if sp.issparse(rna_adata.X) else rna_adata.X,
        index=rna_adata.obs_names,
        columns=rna_adata.var_names,
    )

    logger.info("Computing region-to-gene relationships (method=%s, n_cpu=%d)", importance_scoring_method, n_cpu)
    r2g_df = calculate_regions_to_genes_relationships(
        df_exp_mtx=df_exp,
        df_acc_mtx=df_acc,
        search_space=search_space_df,
        temp_dir=str(r2g_tmp),
        correlation_scoring_method="SR",   # SR = Spearman (required, not default)
        importance_scoring_method=importance_scoring_method,
        n_cpu=n_cpu,
    )

    # --- Step 3: post-hoc filtering ---
    n_before = len(r2g_df)
    r2g_df = r2g_df[
        (r2g_df["importance"] > importance_threshold) &
        (r2g_df["rho"].abs() > rho_threshold)
    ].reset_index(drop=True)
    logger.info(
        "Peak-to-gene filtering: %d → %d links (importance > %.3f, |rho| > %.3f)",
        n_before, len(r2g_df), importance_threshold, rho_threshold,
    )

    # Keep only the columns needed downstream
    keep_cols = [c for c in ["region", "target", "importance", "rho", "Distance"] if c in r2g_df.columns]
    adata.uns["scenicplus_peak_gene_links"] = r2g_df[keep_cols]

    logger.info(
        "multi_grn_peak_to_gene complete: %d peak-gene links stored in "
        "adata.uns['scenicplus_peak_gene_links']",
        len(r2g_df),
    )
    return adata


def _parse_gtf_annotation(gtf_path: Path):
    """Parse TSS annotation DataFrame from a GTF file (offline fallback)."""
    import pandas as pd

    records = []
    with open(gtf_path) as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            fields = line.strip().split("\t")
            if len(fields) < 9 or fields[2] != "transcript":
                continue
            chrom = fields[0]
            if not chrom.startswith("chr"):
                chrom = "chr" + chrom
            start = int(fields[3])
            end = int(fields[4])
            strand = fields[6]
            attrs = dict(
                item.strip().split(" ", 1)
                for item in fields[8].rstrip(";").split(";")
                if " " in item.strip()
            )
            gene_name = attrs.get("gene_name", "").strip('"')
            if not gene_name:
                continue
            tss = start if strand == "+" else end
            records.append({"Chromosome": chrom, "Start": tss, "Strand": strand, "Gene": gene_name})
    df = pd.DataFrame(records).drop_duplicates()
    return df
