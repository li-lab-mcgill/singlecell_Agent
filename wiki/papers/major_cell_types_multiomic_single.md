---
paper_id: major_cell_types_multiomic_single
title: "Major cell-types in multiomic single-nucleus datasets impact statistical modeling of links between regulatory sequences and target genes."
doi: "10.1038/s41598-023-31040-w"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9998442/"
source_ids: {doc_id: "pmc:9998442", pmid: "36894706", pmcid: "9998442", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_peak_to_gene"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Map method classes for peak-to-gene linkage and TF program inference in single-cell multiome and approaches for single-cell GWAS enrichment; identify assumptions and benchmarks applicable to human cortex AD datasets."]
extends: []
added: 2026-05-27
session: unknown
---

## Summary
This study shows that GC/coverage-matched trans-peak null models used by workflows like Signac can lose power for peak-to-gene linkage in multiomic single-nucleus data when dominant cell types are present, due to bimodal null distributions. Using a 10x PBMC multiome dataset, the authors demonstrate that physical distance and raw Pearson correlation outperform Signac-style Z-scores, improving agreement with Epimap and CRISPR perturbation validations.

## Background
Enhancer activity is cell-type specific and difficult to infer in heterogeneous tissues. Single-nucleus multiome assays enable correlating chromatin accessibility with gene expression to score cis-regulatory links, but common practices that form null distributions from GC/coverage-matched trans peaks can be confounded by dataset composition, particularly when a cell type is abundant and drives trans-peak co-accessibility.

## Method and dataset
Analysis of the 10x Genomics PBMC multiome dataset with 11,331 cells (30 annotated cell types; analyses restricted to 17 types with >50 cells). ATAC peaks within 500 kb of TSSs were considered. Peak cell-type specificity was assigned using Presto AUC; links were attributed to cell types accordingly. Peak-gene correlations and Signac Z-scores were computed using GC/coverage-matched trans peaks from other chromosomes. Assumptions include that peak-gene regulatory effects are detectable via correlation across single nuclei and that matched trans peaks provide an appropriate null distribution.

## Analysis
Investigated the impact of dominant cell types (mononuclear phagocytes) by downsampling from 3,782 to 500 cells and comparing Signac Z-scores before/after downsampling. Examined null distribution shapes and identified bimodality due to trans-peak correlations within abundant cell types, using MACS2 peak calls. Tested alternative link-scoring models using (i) genomic distance and (ii) raw Pearson correlation coefficients. Benchmarked Signac Z-scores versus distance and Pearson R using Epimap predictions (e.g., CD14 monocytes) and CRISPR perturbation validations (curated 664 overlapping tests with 51 positives from Nasser et al. 2021). Expanded evaluated links to those with nonzero counts and |R| > 0.01 (approximately 590,842 links) and computed ROC/AUC.

## Key findings
1) GC/coverage-matched trans-peak nulls often become bimodal for peaks specific to abundant cell types, causing loss of power for highly accessible cCREs in dominant cell types. 2) Bimodality arises because abundant cell types contribute more detected peaks and shared TF programs, increasing trans-peak co-accessibility within that cell type. 3) Downsampling the dominant cell type and/or removing its peaks from null sets reduces the bimodal second mode and increases Z-scores for cell-type-specific links. 4) Alternative scoring improves prediction: in CD14 monocytes, AUC versus Epimap increased from 0.51 (Signac Z) to 0.71 (Pearson R); CRISPR validation AUC increased from 0.63 (Signac Z) to 0.73 (Pearson R). 5) Physical distance and raw Pearson correlation are more reliable predictors of peak-gene links than trans-peak-matched Z-scores in this multiomic PBMC dataset.

## Limitations
Analyses are from a single PBMC dataset and specific workflow (Signac with MACS2), limiting generalizability to other tissues and platforms. CRISPR ground truth is limited in number and context and may be biased. Links were restricted to within 500 kb and required minimal correlation, potentially missing distal or weak effects. Cell-type attribution and downsampling choices may affect results, and correlation does not establish causality.

## Metrics used
ROC AUC for link prediction against Epimap (e.g., CD14 AUC 0.51 Signac Z vs 0.71 Pearson R) and CRISPR perturbation validation (AUC 0.63 Signac Z vs 0.73 Pearson R); Presto AUC for peak cell-type specificity; number of validated positives (51 of 664 tests); peak-gene correlation coefficients (Pearson R); Signac Z-scores; evaluated links count (~590,842) and distance to TSS (≤500 kb).
