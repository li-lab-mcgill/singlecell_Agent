---
paper_id: systematic_benchmarking_scatac_2024
title: "Systematic benchmarking of single-cell ATAC-sequencing protocols."
doi: "10.1038/s41587-023-01881-x"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC11180611/"
source_ids: {doc_id: "pmc:11180611", pmid: "37537502", pmcid: "11180611", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_cell_type_annotation", "atac_clustering", "multiomic_integration"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["What are the statistical assumptions, data requirements, and validation for Seurat v4 Weighted Nearest Neighbors (WNN) joint RNA+ATAC embedding and clustering?"]
extends: ["benchmarking_joint_rna_atac_2023"]
added: 2026-05-15
session: unknown
---

## Summary
This paper systematically benchmarks eight scATAC-seq protocols across 47 multicenter experiments on a standardized cryopreserved PBMC reference (two donors mixed 1:1), processes all data with a unified PUMATAC pipeline, and releases ~169,000 PBMC profiles and code. It quantifies protocol-specific differences in library complexity and tagmentation specificity and shows how these differences propagate to peak calling, cell-type annotation, genotype demultiplexing, differential accessibility and motif enrichment, providing practical QC/data-requirement guidance for downstream and multimodal analyses.

## Hypothesis framed
Different scATAC-seq protocols produce systematic, protocol-specific biases in library complexity and tagmentation specificity that materially affect downstream analyses (peak calling, cell-type annotation, genotype demultiplexing, differential accessibility, and motif enrichment), and a unified preprocessing pipeline can harmonize outputs for cross-protocol comparison.

## Questions answered
- Do commonly used scATAC-seq protocols differ in library complexity and tagmentation specificity, and how do these differences affect downstream analyses such as peak calling and cell-type annotation?
- Can a unified preprocessing pipeline (PUMATAC) harmonize disparate scATAC-seq data formats to enable consistent cross-protocol comparison and benchmarking?
- What per-cell QC metrics and experimental design elements (e.g., multicenter technical replicates, mixed-donor reference) are informative boundary conditions for multimodal integration robustness?

## Key findings
Across 47 experiments and ~169,000 PBMC profiles (target ~3,000 cells per sample), protocols exhibited substantial and reproducible differences in sequencing library complexity and tagmentation specificity that propagated to downstream results: sensitivity and specificity of peak detection, accuracy of cell-type annotation and genotype demultiplexing, the number and robustness of differential accessibility calls, and motif-enrichment outcomes. Despite protocol-specific variation, all methods broadly recovered major PBMC cell-type identities. The PUMATAC pipeline enabled consistent cross-protocol processing and facilitated benchmark comparisons.

## Methods used
Multicenter experimental design with technical replicates; benchmarking of eight scATAC-seq methods (10x Genomics variants including multiome and mtscATAC, Bio-Rad ddSEQ, HyDrop, s3-ATAC); universal preprocessing pipeline PUMATAC to harmonize formats and QC; comparisons based on per-cell QC metrics (TSS enrichment, FRIP, unique fragment counts), library complexity, tagmentation specificity; downstream analyses including peak calling, genotype demultiplexing, differential accessibility testing, and transcription factor motif enrichment assessments.

## Method and dataset
Benchmark of eight scATAC-seq protocols applied to cryopreserved human PBMCs (two donors mixed 1:1) processed across multiple centers producing 47 datasets (targeting ~3,000 cells/sample; aggregate ~169,000 single-cell ATAC profiles). Analyses used unified preprocessing (PUMATAC) and compared TSS enrichment, FRIP, unique fragments, library complexity, peak calls, differential accessibility, genotype demultiplexing, and motif enrichment. Assumptions: PBMC mixed-donor reference is an appropriate standardized sample for cross-protocol comparison; technical replicates and a unified pipeline reduce but do not eliminate center/protocol variation.

## Limitations
Benchmarking limited to cryopreserved PBMCs from two donors (1:1 mix), so results may not generalize to other tissues or to rare cell types; multicenter experimental variability cannot be fully eliminated; some protocols had fewer replicates or center representations; not all existing scATAC-seq methods were included; conclusions depend on the specific preprocessing pipeline and parameter choices used.

## Evidence pattern
comparison_design: multicenter, technical-replicate benchmarking across 47 datasets using a standardized mixed-donor PBMC reference; statistical_unit: single cells (per-cell fragment counts); effect_metric: TSS enrichment, FRIP, unique fragment counts, library complexity, peak counts, differential accessibility counts, motif-enrichment scores, cell-type annotation accuracy, genotype demultiplexing accuracy; controls_covariates: 1:1 mixed donors, extraction methods, center; validation: genotype demultiplexing, reproducibility across replicates and centers, mouse brain data as tissue probe; boundary_conditions: protocol- and tissue-dependent performance.

## Extends or contradicts
Extends prior joint integration and benchmarking efforts (e.g., benchmarking_joint_rna_atac_2023) by providing a multicenter, protocol-level empirical benchmark and a large public scATAC-seq PBMC resource; does not report direct contradictions of prior method-comparison conclusions but highlights strong protocol-dependent effects that can influence downstream benchmarking outcomes.

## Boundary conditions
Works when: Applies to cryopreserved human PBMC samples prepared as a 1:1 mix of two donors, with per-sample targets of ~3,000 cells and aggregate datasets on the order of 10^5 cells; requires sufficient sequencing/library complexity to compute per-cell QC metrics (TSS enrichment, FRIP, unique fragment counts) and to perform reliable peak calling and genotype demultiplexing; multicenter technical replicates and unified preprocessing (PUMATAC) enable comparable cross-protocol analyses.
Fails when: Findings and protocol rankings may not generalize when applied to other tissues or to datasets with very low per-cell fragment counts or poor TSS/FRIP metrics (insufficient library complexity), when rare cell types are present at very low abundance, when protocols not included in the benchmark are used, or when substantially different preprocessing pipelines/parameters are applied.
