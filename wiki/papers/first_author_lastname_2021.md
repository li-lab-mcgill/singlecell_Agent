---
paper_id: first_author_lastname_2021
title: "Predicting gene regulatory networks from multi-omics to link genetic risk variants and neuroimmunology to Alzheimer's disease phenotypes."
doi: "10.1101/2021.06.21.449165"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC8240682/"
source_ids: {doc_id: "pmc:8240682", pmid: "34189529", pmcid: "8240682", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "multi_grn_inference"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["methodological requirements for multiomics analyses in AD"]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study performed integrative multi-omics analysis to construct gene regulatory networks (GRNs) that link genetic risk variants and neuroimmunology to Alzheimer's disease (AD) phenotypes, revealing systematic insights into gene regulatory mechanisms. The analysis predicted GRNs across key brain regions and identified potential biomarkers for neuroimmunology in AD.

## Hypothesis framed
Can multi-omics data elucidate the gene regulatory mechanisms linking genetic risk variants to Alzheimer's disease phenotypes?

## Questions answered
- What are the specific gene regulatory networks associated with Alzheimer's disease phenotypes across different brain regions?
- Do AD-Covid genes outperform known Covid-19 genes in predicting severe Covid-19 outcomes?

## Key findings
The study identified GRNs in the Hippocampus, Dorsolateral Prefrontal Cortex (DLPFC), and Lateral Temporal Lobe (LTL) with specific SNPs disrupting TF binding, and AD-Covid genes were found to classify severe Covid-19 patients better than known Covid-19 genes.

## Methods used
Integrative multi-omics analysis including genotype, transcriptomics, and epigenomics; gene co-expression network construction; transcription factor prediction.

## Method and dataset
Constructed gene co-expression networks from population gene expression data; dataset size not specified; relies on the availability and quality of multi-omics data.

## Limitations
The reliance on multi-omics data may be limited by availability and quality, and predictive models require further validation in clinical settings.

## Evidence pattern
entity_definition, comparison_design, statistical_unit, effect_metric, controls_covariates

## Extends or contradicts


## Boundary conditions
Works when: Works when high-quality multi-omics data is available and sufficient sample size is achieved for accurate prediction.
Fails when: Fails when the data is sparse or when significant batch effects are present without correction.
