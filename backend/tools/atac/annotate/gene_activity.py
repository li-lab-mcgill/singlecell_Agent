"""ATAC cell type annotation via gene activity scoring.

Uses snap.pp.make_gene_matrix() to aggregate TN5 insertions over gene bodies,
producing a pseudo-RNA matrix, then annotates with CellTypist.

Requires a genome annotation GTF file.
"""

from __future__ import annotations

from pathlib import Path


def run(
    adata,
    *,
    gtf_path: str | Path,
    celltypist_model: str = "Immune_All_Low.pkl",
    majority_voting: bool = True,
    upstream: int = 2000,
    downstream: int = 0,
) -> object:
    """Annotate ATAC cells via gene activity matrix + CellTypist.

    Pipeline:
      1. Build gene activity matrix from TN5 insertions in gene regulatory
         domains (gene body + upstream promoter) using snap.pp.make_gene_matrix().
      2. Normalize and log-transform.
      3. Run CellTypist on the pseudo-RNA matrix.

    Args:
        adata: AnnData (snapatac2 format with fragment data loaded).
        gtf_path: Path to genome annotation GTF/GFF file (e.g. gencode.v44.gtf.gz).
        celltypist_model: CellTypist model name or .pkl path (default: Immune_All_Low.pkl).
        majority_voting: Refine predictions using majority voting (default True).
        upstream: Promoter extension upstream of TSS in bp (default 2000).
        downstream: Extension downstream of gene end in bp (default 0).

    Returns:
        adata with:
        - adata.obsm["gene_activity"]: gene activity score matrix (sparse)
        - adata.obs["cell_type"]: CellTypist predicted cell types
        - adata.obs["cell_type_conf"]: prediction confidence scores
    """
    import snapatac2 as snap
    import scanpy as sc
    import celltypist

    gtf = Path(gtf_path)
    if not gtf.exists():
        raise FileNotFoundError(
            f"GTF file not found: {gtf}\n"
            "Download from GENCODE: https://www.gencodegenes.org/human/\n"
            "  e.g. gencode.v44.annotation.gtf.gz (human hg38)\n"
            "Or use the gene_annotations resource node to download it."
        )

    # Step 1: build gene activity matrix
    gene_adata = snap.pp.make_gene_matrix(
        adata,
        gene_anno=str(gtf),
        upstream=upstream,
        downstream=downstream,
        include_gene_body=True,
        inplace=False,
    )
    # gene_adata: AnnData (cells × genes)

    # Step 2: normalize for CellTypist
    sc.pp.normalize_total(gene_adata, target_sum=1e4)
    sc.pp.log1p(gene_adata)

    # Store gene activity in original adata for downstream use
    adata.obsm["gene_activity"] = gene_adata.X

    # Step 3: run CellTypist
    predictions = celltypist.annotate(
        gene_adata,
        model=celltypist_model,
        majority_voting=majority_voting,
    )
    annotated = predictions.to_adata()
    label_col = "majority_voting" if majority_voting and "majority_voting" in annotated.obs else "predicted_labels"

    adata.obs["cell_type"] = annotated.obs[label_col].values
    adata.obs["cell_type_conf"] = annotated.obs["conf_score"].values

    return adata
