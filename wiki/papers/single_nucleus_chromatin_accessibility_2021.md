---
paper_id: single_nucleus_chromatin_accessibility_2021
title: "Single-nucleus chromatin accessibility and transcriptomic characterization of Alzheimer's disease."
doi: "10.1038/s41588-021-00894-z"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC8766217/"
source_ids: {doc_id: "pmc:8766217", pmid: "34239132", pmcid: "8766217", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "rna_grn_inference", "rna_trajectory"]
retrieval_goals: ["contradiction"]
retrieval_intents: ["previous studies on AD multiomics regulatory landscapes"]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study performed a multi-omic single-nucleus analysis on 191,890 nuclei in late-stage Alzheimer's disease (AD) to characterize chromatin accessibility and gene expression, revealing significant cellular heterogeneity and disease-associated regulatory elements. The findings may reshape the understanding of gene regulation in AD.

## Hypothesis framed
The gene-regulatory landscape of the brain in late-stage Alzheimer's disease exhibits significant cellular heterogeneity and defines specific cis-regulatory relationships.

## Questions answered
- What cis-regulatory elements are associated with risk genes like APOE and CLU in late-stage AD?
- Which transcription factors are relevant to glial populations in AD?

## Key findings
Identified oligodendrocyte-associated regulatory modules linked to genes APOE and CLU, as well as transcription factors like SREBF1 related to glial populations, indicating distinct regulatory mechanisms in late-stage AD.

## Methods used
Single-nucleus RNA-seq and ATAC-seq integration.

## Method and dataset
Integrated single-nucleus RNA-seq and ATAC-seq analyses on human prefrontal cortex samples from late-stage AD and age-matched controls, comprising 191,890 nuclei, aiming to delineate regulatory mechanisms.

## Limitations
Challenges with data sparsity in single-cell methods were addressed using integration techniques, although potential variability in postmortem human tissue samples remains.

## Evidence pattern
entity_definition, comparison_design, effect_metric

## Extends or contradicts


## Boundary conditions
Works when: works when data includes late-stage AD samples with sufficient nuclei.
Fails when: fails when using highly variable or sparse single-cell data without proper integration methods.
