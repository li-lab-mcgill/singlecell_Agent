---
paper_id: neuronal_reprogramming_cell_cycle_ad
title: "Early neuronal reprogramming and cell cycle reentry shape Alzheimer's disease progression."
doi: "10.1101/2025.06.04.653670"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12157441/"
source_ids: {doc_id: "pmc:12157441", pmid: "40502029", pmcid: "12157441", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_gene_programs"]
retrieval_goals: ["contradiction"]
retrieval_intents: ["Find studies that report neuronal-dominant or early neuronal regulatory/transcriptomic changes in AD to check whether a blanket \"microglia strongest\" claim is overgeneralized."]
extends: []
added: 2026-05-27
session: unknown
---

## Summary
Using non-negative matrix factorization on single-nucleus RNA-seq from the prefrontal cortex of 437 human donors spanning no impairment to AD dementia, the study identifies coordinated, early neuronal gene-program shifts that precede clinical cognitive decline. Neurons rapidly modulate synaptic genes and converge into two programs—oxidative stress/apoptosis (enriched in vulnerable subtypes) and DNA damage/cell-cycle reentry (linked to more resilient subtypes)—with findings validated in independent snRNA-seq, proteomics, and ELISA datasets.

## Background
While AD is characterized by plaques, tangles, synaptic dysfunction, neuronal loss, gliosis, and cognitive decline, prior cell atlases emphasized early glial coordination and subtype-specific neuronal vulnerability without clarifying when neuronal changes emerge, how they differ among neuronal subtypes, or how they align with glial responses. This gap obscures the sequence and coordination of neuro-glial processes shaping AD progression.

## Method and dataset
Applied non-negative matrix factorization to identify co-expression gene programs in single-nucleus RNA-seq profiles from prefrontal cortex tissue of 437 donors covering no cognitive impairment through AD dementia in a cross-sectional design. Assumes non-negativity and additivity of expression programs to capture coordinated gene modules. Program dynamics were evaluated across neuronal subtypes, compared to glial states and non-AD aging, and validated using independent snRNA-seq cohorts plus orthogonal proteomics and ELISA measurements.

## Analysis
Identified neuronal co-expression programs with NMF; quantified program activation across neuronal subtypes and disease states; assessed timing relative to clinical cognitive decline; characterized two convergent neuronal programs (oxidative stress/apoptosis; DNA damage/cell-cycle reentry) and mapped their enrichment to vulnerable versus resilient neuronal subtypes; analyzed coupling between neuronal and glial program activations; contrasted program coupling patterns in AD versus non-AD brain aging; validated program signatures in external snRNA-seq datasets and by concordant changes in proteomics and ELISA.

## Key findings
Neuronal transcriptional reprogramming occurs early in AD and precedes clinical cognitive decline in prefrontal cortex. Across neuronal subtypes, synaptic gene expression is rapidly modulated early in disease. Neurons converge into two major programs: an oxidative stress/apoptosis program enriched in vulnerable neuronal subtypes, and a DNA damage/cell-cycle reentry program associated with more resilient subtypes. Neuronal program activation is tightly coupled with glial responses, and neuron–glia coupling patterns diverge between AD and non-AD aging. Findings were replicated across independent snRNA-seq datasets and showed concordance with proteomics and ELISA.

## Limitations
Cross-sectional observational design limits causal and temporal inference; analysis confined to prefrontal cortex may not generalize to other brain regions; potential technical/modeling biases from snRNA-seq and NMF; post-mortem confounds persist; functional consequences of neuronal cell-cycle reentry are inferred rather than directly tested.

## Metrics used
Validation endpoints: replication of neuronal gene programs in independent snRNA-seq datasets; concordance of program-associated proteins with proteomics and ELISA; qualitative timing relative to clinical cognitive decline; statistical unit: donor/sample.
