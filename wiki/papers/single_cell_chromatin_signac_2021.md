---
paper_id: single_cell_chromatin_signac_2021
title: "Single-cell chromatin state analysis with Signac."
doi: "10.1038/s41592-021-01282-5"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9255697/"
source_ids: {doc_id: "pmc:9255697", pmid: "34725479", pmcid: "9255697", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_peak_to_gene", "atac_motif_analysis", "multiomic_integration"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["peak-to-gene linking (Signac LinkPeaks)", "co-accessibility (Cicero compatibility)", "TF activity (chromVAR integration)"]
extends: []
added: 2026-05-27
session: unknown
---

## Summary
Signac is an R/Seurat-integrated toolkit for end-to-end analysis of single-cell chromatin data, including peak calling, QC, dimensionality reduction, clustering, motif analysis, multiomic integration, and peak-to-gene linking (LinkPeaks). The framework introduces a ChromatinAssay for efficient chromatin data handling and demonstrates scalability to datasets exceeding 700,000 cells.

## Background
The rise of single-cell chromatin assays demands scalable, interoperable computational tools that support QC, feature quantification, dimensionality reduction, clustering, motif analysis, and integration with other single-cell modalities such as RNA and protein.

## Method and dataset
Signac (v1.2.0; R 4.0.3) introduces a ChromatinAssay class compatible with Seurat that stores genomic ranges, gene annotations, genome build, DNA motif information, and tabix-indexed fragment files. The toolkit supports single-cell chromatin accessibility analyses and multimodal integration; it demonstrates on public 10x Genomics PBMC multiome (joint RNA+ATAC) data and scales to >700,000 cells on Ubuntu 18.04.4 using standard BLAS/LAPACK. LinkPeaks performs peak-to-gene linking via cross-cell correlations between peak accessibility and gene expression in multiome data, assuming that correlated variability across cells indicates regulatory relationships.

## Analysis
Workflow includes peak calling and quantification; QC using TSS enrichment and nucleosome banding strength; dimensionality reduction with a modified LSI; clustering; motif analysis; and interactive visualization within Seurat. The authors demonstrate seamless interoperability with third-party tools (chromVAR for TF motif activity, Monocle, Cicero for co-accessibility, Harmony for integration). Multiomic integration is shown on 10x PBMC multiome data; peak-to-gene linking is carried out using cross-cell correlations (LinkPeaks).

## Key findings
A simple modification to LSI improved dimensionality reduction for low-sensitivity single-cell chromatin datasets. The Signac framework scaled to analyze datasets with more than 700,000 cells and enabled end-to-end analysis and visualization of PBMC multiome (RNA+ATAC) data. Signac interoperated with community tools such as chromVAR and Cicero within the Seurat ecosystem.

## Limitations
Demonstrations focus mainly on DNA accessibility; other chromatin modalities are not extensively benchmarked. Detailed assumptions, controls, and benchmarking for peak-to-gene linking beyond cross-cell correlation are not provided. Very low-sensitivity datasets remain challenging despite the modified LSI, and reliance on the R/Seurat ecosystem and specified computing environments may limit adoption.

## Metrics used
TSS enrichment; nucleosome banding strength; dataset scale (number of cells processed, >700,000).
