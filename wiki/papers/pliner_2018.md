---
paper_id: pliner_2018
title: "Cicero Predicts cis-Regulatory DNA Interactions from Single-Cell Chromatin Accessibility Data."
doi: "10.1016/j.molcel.2018.06.044"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC6582963/"
source_ids: {doc_id: "pmc:6582963", pmid: "30078726", pmcid: "6582963", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_peak_to_gene", "atac_motif_analysis", "atac_grn_inference"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Determine which computational method classes are used to integrate paired snRNA-seq and snATAC-seq and infer peak-to-gene or cis-regulatory links from the same cells, and what assumptions they make."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This paper introduces Cicero, an algorithm that predicts co-accessible pairs of cis-regulatory DNA elements from single-cell chromatin accessibility data and links distal accessible elements to putative target genes. The authors apply Cicero to optimized sci-ATAC-seq profiles from human skeletal muscle myoblast differentiation and show that co-accessible element groups resemble chromatin hubs associated with physical proximity, shared transcription factor logic, histone-mark dynamics, and gene-expression changes.

## Hypothesis framed
Single-cell chromatin accessibility covariation can identify co-accessible cis-regulatory DNA elements whose links reflect spatially or functionally related chromatin hubs and can improve assignment of distal regulatory elements to target genes.

## Questions answered
- Can co-accessibility estimated from single-cell ATAC-seq identify distal regulatory DNA elements that are physically proximal or functionally linked in cis?
- Do Cicero-linked distal elements improve prediction of gene-expression dynamics compared with promoter accessibility alone?
- During human myoblast differentiation, do dynamically accessible elements remain organized in stable chromatin hubs or reorganize extensively?

## Key findings
Cicero-linked regulatory elements were enriched for physical proximity, shared transcription factor regulatory logic, and coordinated histone-mark changes. In human skeletal muscle myoblast differentiation, distal elements linked to promoters by Cicero improved prediction of gene-expression dynamics compared with promoter accessibility alone, especially when transcription factor motif information was included. Most DNA elements remained within chromatin hubs throughout differentiation, while a subset of MYOD1-bound elements opened early in a PBX1- and MEIS1-dependent manner.

## Methods used
Optimized sci-ATAC-seq profiling, quality filtering and removal of likely fibroblasts, pseudotime ordering of differentiating myoblasts, Cicero co-accessibility analysis to identify covarying accessible element pairs and cis-co-accessibility networks, promoter-distal element linking, comparison with bulk ATAC-seq and DNase-seq, validation against physical proximity data, histone-mark dynamics, transcription factor motif enrichment, MYOD1 binding, and gene-expression changes.

## Method and dataset
Cicero was applied to single-cell chromatin accessibility profiles from human skeletal muscle myoblasts sampled at 0, 24, 48, and 72 hours of differentiation using optimized sci-ATAC-seq, yielding 13,367 cells across two experiments after analysis-level filtering and excluding likely fibroblasts. The method infers links among accessible genomic elements by correlated accessibility across single cells and uses those links to connect distal regulatory elements to promoters or other regulatory sites. It assumes that co-accessibility across cells reflects shared regulatory programs or cis spatial/functional interactions, and that the dataset has sufficient cell-state variation, sequencing coverage, accurate peak calls, and appropriate cell filtering.

## Limitations
Cicero infers putative regulatory interactions from correlated accessibility and does not directly prove physical chromatin contact or functional enhancer-gene regulation. Co-accessibility can arise from shared cell-state dynamics or common transcription factor activity rather than direct cis interaction. The main application is human skeletal muscle myoblast differentiation, so performance may vary across cell types, genomic contexts, sequencing depth, heterogeneity levels, peak-calling quality, and pseudotime-ordering accuracy. The study does not perform paired snRNA-seq/snATAC-seq multiome integration or direct matched expression-accessibility peak-to-gene modeling from the same cells.

## Evidence pattern
Entity definition: defines Cicero links as pairs of accessible DNA elements with covarying accessibility across single cells. Statistical unit: single cells and accessible genomic elements from sci-ATAC-seq. Effect metric: co-accessibility/correlation-derived links among regulatory elements and promoters. Validation: compared Cicero links with physical proximity data, transcription factor motif enrichment, histone-mark dynamics, bulk ATAC-seq, DNase-seq, MYOD1 binding, and gene-expression changes. Boundary conditions: evaluated in a time-course differentiation system with substantial cell-state variation.

## Extends or contradicts


## Boundary conditions
Works when: Works when single-cell ATAC-seq or sci-ATAC-seq data contain enough cells and accessibility coverage to estimate covariation across accessible elements, when there is biological cell-state variation such as differentiation, and when peaks, cell filtering, and trajectory or cell-state structure are reliable. The demonstrated dataset had 13,367 cells across 0, 24, 48, and 72 hour myoblast differentiation time points.
Fails when: May fail or produce indirect links when accessibility coverage is too sparse, accessible elements are rarely observed, cell filtering or peak calling is poor, pseudotime or cell-state ordering is inaccurate, or correlations are dominated by broad cell-state effects, batch effects, or shared transcription factor activity rather than direct cis regulation. It does not directly address paired multiome data, matched gene expression-accessibility modeling, or proof of functional enhancer-gene causality.
