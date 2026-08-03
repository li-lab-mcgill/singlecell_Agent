---
paper_id: characterizing_cis_regulatory_2023
title: "Characterizing cis-regulatory elements using single-cell epigenomics."
doi: "10.1038/s41576-022-00509-1"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9771884/"
source_ids: {doc_id: "pmc:9771884", pmid: "35840754", pmcid: "9771884", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "atac_peak_to_gene", "atac_grn_inference"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Determine which computational method classes are used to integrate paired snRNA-seq and snATAC-seq and infer peak-to-gene or cis-regulatory links from the same cells, and what assumptions they make."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This review synthesizes recent single-cell epigenomic and multi-omic technologies for identifying and characterizing cis-regulatory elements, including chromatin accessibility, DNA methylation, histone modification, chromatin conformation, and combined molecular profiles. It emphasizes how these methods can resolve cell type-specific regulatory programs that are obscured in bulk epigenomic data and discusses their readiness for human tissue profiling.

## Hypothesis framed
Single-cell epigenomic and multi-omic profiling can identify and characterize cell type-specific cis-regulatory elements more precisely than bulk profiling, enabling regulatory programs to be linked to development, environmental responses, disease, and noncoding genetic variation.

## Questions answered
- Which single-cell epigenomic modalities can be used to characterize promoters, enhancers, and other cis-regulatory elements?
- How can single-cell multi-omic data help connect cis-regulatory elements to cell type-specific gene programs?
- What technical and computational limitations currently constrain CRE-to-gene linking and human tissue profiling with single-cell epigenomics?

## Key findings
The review concluded that single-cell epigenomic and multi-omic assays provide higher-resolution views of cis-regulatory element activity than bulk transcriptomic and epigenomic approaches, particularly for heterogeneous tissues. It found that these methods can reveal cell type-specific regulatory landscapes, developmental trajectories, environmental responses, and disease-associated regulatory changes, but that distal CRE-to-gene linking remains difficult because of sparse data, technical noise, and computational complexity.

## Methods used
Narrative review and synthesis of single-cell epigenomic assay classes and analytical tools, covering chromatin accessibility profiling, DNA methylation profiling, histone modification profiling, chromatin conformation profiling, multi-omic profiling, cell type and state identification, regulatory program inference, and CRE-to-target-gene linking.

## Method and dataset
No new primary dataset or quantitative benchmark was presented. The paper reviewed computational and experimental method classes applied to single-cell epigenomic and multi-omic data, including scATAC-seq, single-cell DNA methylation, single-cell histone modification, single-cell chromatin conformation, and combined transcriptome-epigenome profiles. The summary does not report approximate dataset sizes or explicit assumptions for individual peak-to-gene or cis-regulatory link inference methods.

## Limitations
This is a review rather than a primary experimental study and does not provide new data, direct validation experiments, or quantitative benchmarking of CRE-to-gene inference accuracy. The summary reports ongoing limitations including sparse single-cell epigenomic measurements, technical noise, limited throughput for some assays, difficulty linking distal cis-regulatory elements to target genes, computational complexity, and insufficient standardization for routine large-scale human tissue profiling.

## Evidence pattern
Evidence is based on entity definition, comparison design, and boundary-condition synthesis. The paper defines CRE classes by epigenomic features, compares bulk versus single-cell epigenomic and multi-omic profiling conceptually, and describes boundary conditions and failure modes such as sparsity, noise, and difficulty assigning distal regulatory elements to target genes.

## Extends or contradicts
The review extends prior bulk CRE cataloguing efforts by summarizing how single-cell epigenomic and multi-omic approaches can resolve cell type-specific regulatory programs that bulk methods average across heterogeneous populations. It does not directly contradict a specific prior paper in the provided summary.

## Boundary conditions
Works when: Works when the research question requires cell type-specific regulatory information in heterogeneous samples, such as human tissues, developmental contexts, environmental responses, disease pathogenesis, or interpretation of noncoding genetic variation. It is most relevant when chromatin accessibility, DNA methylation, histone modification, chromatin conformation, or multi-omic measurements are available at single-cell resolution.
Fails when: Known failure modes include highly sparse or noisy single-cell epigenomic data, assays with limited throughput, insufficient information to link distal CREs to target genes, complex multi-modal analyses without adequate computational support, and settings requiring standardized, quantitatively validated large-scale human tissue profiling workflows.
