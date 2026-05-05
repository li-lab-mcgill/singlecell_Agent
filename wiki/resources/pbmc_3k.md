---
type: resource
id: pbmc_3k
modality: rna
source: 10x Genomics
url: https://www.10xgenomics.com/resources/datasets/3k-pbmcs-from-a-healthy-donor-1-standard-1-1-0
---

3,000 human PBMCs profiled with 10x Chromium v2 (RNA-seq only). The canonical introductory dataset for scanpy tutorials and the most widely used benchmark for scRNA-seq clustering and annotation.

Key properties:
- Cells: ~2,700 PBMCs after QC
- Modality: RNA only
- Ground truth: 9 cell types at coarse level; fine-grained subtypes available via Seurat/Azimuth annotations
- Format: 10x MEX format (matrix.mtx, barcodes.tsv, genes.tsv)

Well-characterized cell types: CD4 T cells, CD8 T cells, NK cells, B cells, CD14+ monocytes, FCGR3A+ monocytes, dendritic cells, megakaryocytes, others.

Load with: `sc.read_10x_mtx("filtered_gene_bc_matrices/hg19/")`

This dataset is single-batch — batch correction tools should not be applied. Use `pbmc_multiome_10k` for multi-omic tests or any multi-batch benchmark dataset for batch correction evaluation.
