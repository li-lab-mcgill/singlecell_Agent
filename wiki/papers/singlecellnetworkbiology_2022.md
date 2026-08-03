---
paper_id: singlecellnetworkbiology_2022
title: "Single-cell network biology characterizes cell type gene regulation for drug repurposing and phenotype prediction in Alzheimer's disease."
doi: "10.1371/journal.pcbi.1010287"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9333448/"
source_ids: {doc_id: "pmc:9333448", pmid: "35849618", pmcid: "9333448", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "rna_grn_inference"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["methodological requirements for multiomics analyses in AD"]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study integrates single-cell multi-omics datasets to explore gene regulatory networks across four major cell types in Alzheimer's disease, providing insights for drug repurposing and phenotype predictions. It identifies key transcription factors and highlights significant regulatory changes in microglia compared to other cell types.

## Hypothesis framed
Gene regulation at the cell type level in Alzheimer's disease can be characterized using single-cell multi-omics data.

## Questions answered
- What are the common hub transcription factors across different cell types in Alzheimer's disease?
- How do gene regulatory networks differ between control and Alzheimer's disease brains?

## Key findings
Common hub transcription factors were identified across cell types, with significant regulatory changes noted particularly in microglia. The study reveals cell type-specific network modularity linked to AD-risk genes and demonstrates that the predicted genes can accurately forecast clinical phenotypes.

## Methods used
Integrated single-cell transcriptomic, chromatin interaction, and transcription factor binding data, employing machine learning for gene prioritization.

## Method and dataset
Implemented a network-based machine learning analysis on single-cell multi-omics datasets focusing on excitatory neurons, inhibitory neurons, microglia, and oligodendrocytes in control and AD brains, with approximately four major cell types analyzed.

## Limitations
The analysis was limited by dataset availability and focused exclusively on four major cell types.

## Evidence pattern
entity_definition, comparison_design, validation

## Extends or contradicts


## Boundary conditions
Works when: Works when data includes comprehensive single-cell multi-omics for the specified cell types in Alzheimer's disease.
Fails when: Fails when there are significant missing data or if only individual cell types are considered, as well as in datasets lacking robust characterization of AD pathology.
