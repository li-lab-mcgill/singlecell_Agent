---
paper_id: archr_2021
title: "ArchR is a scalable software package for integrative single-cell chromatin accessibility analysis."
doi: "10.1038/s41588-021-00790-6"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC8012210/"
source_ids: {doc_id: "pmc:8012210", pmid: "33633365", pmcid: "", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_peak_to_gene", "atac_motif_analysis", "multiomic_integration"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Identify canonical method papers for peak-to-gene linking and extract assumptions, controls, and validations"]
extends: []
added: 2026-05-27
session: unknown
---

## Summary
ArchR is an end-to-end, scalable R toolkit for single-cell chromatin accessibility analysis that implements QC, clustering, unified peak calling, trajectories, TF footprinting/motif analysis, peak-to-gene linkage, gene activity inference, and streamlined integration with scRNA-seq. Its HDF5-based Arrow architecture enables efficient I/O and analysis of over 1.2 million cells in ~8 hours on a standard Unix laptop.

## Background
scATAC-seq enables cell-resolved mapping of regulatory elements, but existing tools have struggled with scalability and comprehensive workflows, often failing beyond ~80,000 cells or lacking key modules such as robust peak-to-gene linking and multi-omic integration. A unified, memory-efficient framework was needed to perform end-to-end analyses on large datasets.

## Method and dataset
Method: ArchR ingests aligned BAM/fragment files and stores data in compressed, random-access HDF5 Arrow files with chromosome-wise chunked I/O; analyses operate via an in-memory ArchR Project object with heavy data on disk. Peak-to-gene linking is performed by correlating peak accessibility with gene scores across denoised cell aggregates, using distance constraints and a background-matched null that controls for GC content and overall accessibility; optional multi-omic integration with scRNA-seq can further support linkage. TF analysis includes motif enrichment and transcription factor footprinting. Datasets: diverse scATAC-seq collections including PBMCs (discrete cell types), bone marrow (continuous hierarchy), and a multi-organ mouse atlas, scaling to >1.2 million cells. Assumptions: correlation across aggregated cells reflects regulatory coupling; distance to TSS constrains plausible regulatory interactions; background matching by GC content and accessibility approximates a valid empirical null for bias control; scRNA-based integration can serve as orthogonal support for linkage.

## Analysis
Implemented end-to-end scATAC-seq workflow: QC and doublet removal; dimensionality reduction and clustering; unified peak set generation; trajectory inference; TF motif enrichment and footprinting; imputed gene activity/mRNA prediction; peak-to-gene linkage using correlations across denoised cell aggregates with GC/content and accessibility-matched background null and genomic distance filters; optional integration with scRNA-seq to harmonize cell identities and support linkage. Engineering: HDF5 Arrow files with chromosome-wise parallel I/O to reduce memory/runtime; operations orchestrated through an ArchR Project. Benchmarking: compared against commonly used tools (e.g., SnapATAC, Signac; specific versions) across PBMCs, bone marrow, and a multi-organ mouse atlas; evaluated runtime, storage footprint, and scalability.

## Key findings
ArchR scaled to analysis of over 1.2 million single cells in approximately 8 hours on a standard Unix laptop while maintaining smaller Arrow file footprints than input fragment files. The peak-to-gene linking framework with GC/accessibility-matched background nulls and distance constraints, coupled with optional scRNA-seq integration, yielded biologically consistent regulatory element–gene associations validated against external modalities. The unified pipeline delivered robust clustering, trajectory reconstruction, TF footprinting/motif analyses, and gene activity inference across PBMCs, bone marrow, and multi-organ mouse datasets.

## Limitations
Benchmarking was against specific versions of comparator tools, so relative performance may change. Analyses primarily used hg19/mm9 references, potentially limiting immediate applicability to newer builds without adaptation. Performance and runtime claims depend on dataset characteristics and hardware. Some modules (e.g., gene activity inference and multi-omic integration) inherit assumptions of scATAC-seq and external references. Implementation is R-based and optimized for Unix-like systems.

## Metrics used
Runtime (approximately 8 hours for >1.2 million cells), scalability (number of cells processed), storage footprint (Arrow files smaller than input fragments), comparative benchmarking against SnapATAC and Signac on PBMCs, bone marrow, and mouse atlas datasets.
