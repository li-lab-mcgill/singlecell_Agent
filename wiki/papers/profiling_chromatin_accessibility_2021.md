---
paper_id: profiling_chromatin_accessibility_2021
title: "Profiling Chromatin Accessibility at Single-cell Resolution."
doi: "10.1016/j.gpb.2020.06.010"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC8602754/"
source_ids: {doc_id: "pmc:8602754", pmid: "33581341", pmcid: "8602754", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "atac_peak_to_gene", "atac_clustering"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Identify the main computational method classes for paired single-cell multiome RNA+ATAC integration and CRE-to-gene linkage, including assumptions, inputs, outputs, and failure modes for sparse brain nuclei data."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This review summarizes experimental and computational approaches for profiling chromatin accessibility at single-cell resolution, with emphasis on scalable scATAC-seq, multimodal chromatin-plus-RNA or chromatin-plus-protein assays, and integration of chromatin accessibility with transcriptomic and proteomic data. It matters for single-cell genomics because it organizes how sparse chromatin accessibility measurements can be used to discover cell states, infer regulatory programs, and connect cis-regulatory element accessibility to gene expression.

## Hypothesis framed
Single-cell chromatin accessibility profiling, especially when integrated with transcriptomic or proteomic measurements, can reveal cell-to-cell regulatory variation and improve interpretation of transcriptional programs underlying cellular heterogeneity and plasticity.

## Questions answered
- Which experimental approaches can jointly profile chromatin accessibility with RNA or protein abundance in single cells?
- What computational strategies are used to process sparse scATAC-seq data, identify cell populations, and integrate chromatin accessibility with transcriptomic measurements?
- What limitations affect peak-to-gene linkage and regulatory element interpretation in single-cell chromatin accessibility data?

## Key findings
The review concluded that single-cell chromatin accessibility profiling can identify cell types and states, map accessible cis-regulatory elements, infer transcription factor activity, and help explain regulatory control of gene expression. It also concluded that joint chromatin-RNA or chromatin-protein profiling improves interpretation by connecting regulatory element accessibility to functional molecular outputs, but sparse and noisy scATAC-seq data make clustering, peak detection, and peak-to-gene linkage difficult.

## Methods used
Narrative review of single-cell chromatin accessibility assays, including scATAC-seq and multimodal assays such as scCAT-seq and sci-CAR-seq, plus review of bioinformatic workflows for sparse scATAC-seq processing, cell population identification, regulatory element-to-gene linkage, cross-modality integration, and prediction of chromatin accessibility from scRNA-seq data.

## Method and dataset
No original dataset or benchmark was reported in the summary. The paper reviewed data types including single-cell ATAC-seq, joint chromatin accessibility plus transcriptome assays, and joint chromatin accessibility plus proteome assays; the reviewed approaches assume that chromatin accessibility marks regulatory DNA available to DNA-binding proteins and that integration with RNA or protein measurements can connect regulatory state to cellular output.

## Limitations
The paper is a broad review rather than a focused quantitative benchmark. It does not provide a focused comparison of paired single-cell multiome RNA+ATAC integration methods, explicit assumptions and outputs for each method class, quantitative benchmarking of CRE-to-gene linkage, brain nuclei-specific failure modes, enhancer-gene validation strategies, or method-choice guidance among tools such as ArchR, Signac, Cicero, Seurat WNN, SnapATAC, or MOFA+.

## Evidence pattern
Entity definition and boundary-condition review: the paper defines assay classes and computational task classes for single-cell chromatin accessibility, summarizes reported use cases for multimodal integration and regulatory linkage, and identifies sparsity, noise, throughput, coverage, cost, and experimental complexity as boundary conditions.

## Extends or contradicts


## Boundary conditions
Works when: Applies to single-cell datasets measuring genome-wide chromatin accessibility, especially scATAC-seq, and to multimodal designs where chromatin accessibility is jointly measured with transcriptome or proteome data. Integration is most useful when chromatin accessibility and RNA or protein measurements can be used together to connect accessible regulatory elements with cellular outputs.
Fails when: Performance is limited when scATAC-seq data are highly sparse or technically noisy, when chromatin coverage is insufficient for robust clustering or regulatory element detection, when peak-to-gene links are inferred without validation, or when multi-omic assays impose throughput, coverage, cost, or experimental-complexity trade-offs. Predictions of chromatin accessibility from transcriptomic data remain indirect and require careful validation.
