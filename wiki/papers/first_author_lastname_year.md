---
paper_id: first_author_lastname_year
title: "Single-nucleus multiome analysis of human cerebellum in Alzheimer's disease-related dementia."
doi: "10.21203/rs.3.rs-4871032/v1"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC11343296/"
source_ids: {doc_id: "pmc:11343296", pmid: "39184089", pmcid: "11343296", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_peak_to_gene", "multi_grn_inference", "rna_grn_inference"]
retrieval_goals: ["contradiction"]
retrieval_intents: ["previous studies on AD multiomics regulatory landscapes"]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study provides a comprehensive analysis of single-nucleus multiome data from the human cerebellum to uncover transcriptional and epigenomic alterations in Alzheimer's disease (AD) and related dementias. It identifies significant gene-chromatin linkages, disease-relevant transcription factors, and potential causal genes, thereby advancing the understanding of AD at a cellular level.

## Hypothesis framed
Cell type-specific transcriptional and epigenomic changes in the human cerebellum contribute to the pathology of Alzheimer's disease and AD-related dementias.

## Questions answered
- What are the cell type-specific transcriptional changes in the cerebellum of AD patients?
- Which transcription factors and genes are implicated in the pathology of AD in cerebellar cells?

## Key findings
The study identified 431,834 significant linkages between gene expression and chromatin accessibility in cerebellar cells, particularly highlighting RORA and ELF1 in Purkinje and granule cells. Additionally, SEZ6L2 and KANSL1 were prioritized as likely causal genes in these populations.

## Methods used
Single-nucleus RNA sequencing (snRNA-seq) and single-nucleus ATAC sequencing (snATAC-seq) for multiome analysis.

## Method and dataset
snRNA-seq and snATAC-seq were conducted on 103,861 nuclei from cerebellum samples of 9 AD/ADRD cases and 8 controls, along with frontal cortex samples from 6 AD donors for comparison; relies on peak-to-gene linkage analysis for exploring interactions.

## Limitations
The study is based on a limited number of samples, which may not fully encapsulate the heterogeneity of AD/ADRD pathology.

## Evidence pattern
The paper utilized peak-to-gene linkage analysis to establish the connections between gene expression and chromatin accessibility, supported by statistical analysis of significant linkages.

## Extends or contradicts
This study's findings may contradict existing literature by providing new insights into regulatory landscapes in AD.

## Boundary conditions
Works when: Works when analyzing data from multiple cell types with adequate sample sizes, particularly in relation to AD pathology.
Fails when: May not apply in cases with low sample diversity or when investigating only single cell types in isolation.
