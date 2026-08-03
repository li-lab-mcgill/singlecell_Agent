---
paper_id: shiny_sc_2026
title: "ShinySC: An R/Shiny-based desktop application for seamless analysis of scRNA-Seq data."
doi: "10.1016/j.bj.2025.100885"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12860678/"
source_ids: {doc_id: "pmc:12860678", pmid: "40609640", pmcid: "12860678", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_cell_type_annotation", "rna_clustering", "rna_batch_correction"]
retrieval_goals: ["broad_background"]
retrieval_intents: ["Retrieve canonical PBMC scRNA marker references defining major immune cell markers and T/B/monocyte/DC/NK subsets"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
ShinySC is an R/Shiny desktop (and Docker web) application that provides a GUI for end-to-end scRNA-seq analysis, supporting multiple input formats and multiple automatic annotation strategies including SingleR, ScType, scCATCH and GPT-4-based GPTCelltype. The tool was benchmarked for scalability (up to ~200,000 cells on a 64 GB RAM desktop) and validated on PBMC3k (2,700 cells) and the Kang interferon-beta PBMC dataset (~15,000 cells), where it recovered major immune cell types and condition-specific transcriptional responses.

## Hypothesis framed
A unified R/Shiny desktop GUI (ShinySC) that integrates common scRNA-seq analysis steps and multiple annotation strategies can enable non-programming users to perform end-to-end scRNA-seq analyses, accurately annotate major cell types in PBMC datasets, and scale to large datasets on standard desktop hardware.

## Questions answered
- Can a desktop R/Shiny GUI (ShinySC) perform end-to-end scRNA-seq analysis and accurately annotate major cell types in PBMC datasets without programming?
- Can ShinySC scale to datasets of order 10^5 cells on a standard desktop (64 GB RAM) while performing common tasks (QC, clustering, annotation)?
- Does integrating reference-based, marker-based and GPT-based automatic annotation methods in one interface enable concordant cell-type labeling and manual refinement for PBMC data?

## Key findings
ShinySC recovered major immune cell types in PBMC demonstration datasets (PBMC3k, 2,700 cells; Kang interferon-beta PBMC, ~15,000 cells) and captured condition-specific interferon-beta transcriptional responses. The application was benchmarked to process datasets up to ~200,000 cells on a standard desktop with 64 GB RAM (runtime dependent on task and annotation method). It supports multiple input formats (10x MEX/HDF5, AnnData .h5ad, H5Seurat, BD Rhapsody, CellView, Seurat v5) and multiple automatic annotation tools (SingleR, ScType, scCATCH, GPTCelltype) with side-by-side comparison and manual label refinement.

## Methods used
Implementation in R/Shiny (Shiny Dashboard) and DesktopDeployR; modules include data import (10x MEX/HDF5, AnnData .h5ad, H5Seurat, BD Rhapsody, CellView, Seurat v5), QC (cell/gene filtering), feature selection (variable genes), dimensionality reduction (PCA, UMAP, t-SNE), graph-based clustering (adjustable resolution), marker gene identification, automatic annotation (SingleR, ScType, scCATCH, GPT-4-based GPTCelltype), batch correction, differential expression (intra- and inter-condition), and trajectory inference. Benchmarking experiments on desktop hardware measured memory usage and runtime up to ~200k cells.

## Method and dataset
ShinySC wraps standard scRNA-seq analytical methods applied to preprocessed count matrices or Seurat/AnnData-style objects. Demonstrations used PBMC3k (2,700 cells) and the Kang et al. interferon-beta PBMC dataset (~15,000 cells); scalability benchmarks were run up to ~200,000 cells on a desktop with 64 GB RAM. The tool assumes input as preprocessed count matrices / Seurat / AnnData objects (not raw FASTQ) and relies on underlying annotation databases for SingleR/ScType/scCATCH or GPT-based label generation.

## Limitations
Performance and runtime depend on dataset size and chosen methods; practical scaling was benchmarked up to 200,000 cells on systems with ~64 GB RAM so larger datasets or lower-resource machines may be constrained. ShinySC does not perform read-level processing from raw FASTQ. Automated annotations (including GPT-based) may require manual review and refinement. The paper provides limited head-to-head benchmarking of annotation accuracy and runtime against all alternative tools across diverse biological datasets.

## Evidence pattern
entity_definition; validation (demonstrations on PBMC3k and Kang IFN dataset and benchmarking up to 200k cells); boundary_conditions (reported memory/runtime limits on 64 GB RAM desktop)

## Extends or contradicts
Extends practical tool-integration and package-selection concerns (related to impact_package_selection_2024) by packaging multiple analysis and annotation packages into a unified GUI for non-programming users.

## Boundary conditions
Works when: Input are preprocessed count matrices or Seurat/AnnData objects; typical dataset sizes up to ~200,000 cells on a desktop with ~64 GB RAM; annotation accuracy relies on applicability of SingleR/ScType/scCATCH reference marker databases or GPT-based label suggestions; used for standard PBMC-like peripheral blood immune cell compositions.
Fails when: Raw FASTQ-to-count processing is required (ShinySC does not perform read-level alignment/quantification); datasets substantially larger than ~200,000 cells on machines with ≤64 GB RAM may exceed memory/runtime limits; automated annotations may be unreliable for tissue types or rare/novel cell states not represented in underlying reference/marker databases or when GPT-based labels are unreviewed.
