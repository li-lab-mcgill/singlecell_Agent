---
paper_id: cell_type_specific_2026
title: "Cell type-specific gene regulatory atlas prioritizes drug targets and repurposable medicines in Alzheimer's disease."
doi: "10.1101/gr.280436.125"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12951949/"
source_ids: {doc_id: "pmc:12951949", pmid: "41565468", pmcid: "12951949", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "atac_grn_inference", "rna_differential_expression"]
retrieval_goals: ["contradiction"]
retrieval_intents: ["previous studies on cis-regulatory elements and gene expression in Alzheimer's disease"]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study presents a cell type-specific regulatory atlas of the human middle temporal gyrus, leveraging single-nucleus RNA-seq and ATAC-seq data to identify therapeutic opportunities in Alzheimer's disease. It identifies 141 ADNC-associated genes and nine candidate repurposable drugs, highlighting the potential for targeted therapies.

## Hypothesis framed
We hypothesize that a cell type-specific regulatory atlas can uncover disease mechanisms and identify therapeutic opportunities in Alzheimer's disease.

## Questions answered
- What are the gene regulatory networks involved in Alzheimer's disease?
- Which candidate drugs can be repurposed based on identified ADNC-associated genes?

## Key findings
Identified 141 ADNC-associated genes and nine candidate repurposable drugs through gene set enrichment and network proximity analysis, with differential gene expression observed in six major brain cell types at severe AD neuropathological change.

## Methods used
Single-nucleus RNA-seq, ATAC-seq, gene set enrichment analysis, network proximity analysis.

## Method and dataset
Single-nucleus RNA-seq and ATAC-seq, analyzing 1,197,032 nuclei and 740,875 nuclei from 84 donors across four stages of Alzheimer's disease.

## Limitations
Focuses on specific brain regions and lacks longitudinal progression data; challenges in overcoming complex mechanisms of AD and addressing cellular heterogeneity.

## Evidence pattern
entity_definition, comparison_design, statistical_unit, effect_metric, controls_covariates, validation

## Extends or contradicts
This study contradicts previous studies that lack detailed integration of cis-regulatory elements and gene expression analyses in Alzheimer's disease.

## Boundary conditions
Works when: Works when multiomic data from multiple stages of AD is available and analyzed.
Fails when: Fails when longitudinal data is needed for individual progression or when the mechanisms of AD complexity are not addressed.
