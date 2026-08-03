---
paper_id: mapt_expression_2023
title: "MAPT expression is mediated by long-range interactions with cis -regulatory elements."
doi: "10.1101/2023.03.07.531520"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC10120716/"
source_ids: {doc_id: "pmc:10120716", pmid: "37090552", pmcid: "10120716", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_differential_accessibility", "multiomic_integration", "rna_differential_expression"]
retrieval_goals: ["contradiction"]
retrieval_intents: ["Prior work exploring CREs and transcription factor interactions in AD."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study identifies candidate cis-regulatory elements (cCREs) that mediate MAPT expression in neural progenitor cells and differentiated neurons, revealing their potential role in neurodegeneration risk. It finds that disruptions in MAPT enhancer activity may offer protection against Alzheimer's disease.

## Hypothesis framed
MAPT expression is mediated by long-range interactions with cCREs in neural progenitor cells and differentiated neurons.

## Questions answered
- What are the candidate cCREs for MAPT expression in neurons?
- Do variants in these cCREs influence the risk of Alzheimer's disease?

## Key findings
Nominated 94 candidate cCREs for MAPT; 11 regions enhanced transcription in luciferase assays, with 5 regions shown to be necessary for MAPT expression. Variants disrupting these cCREs were less frequent in Alzheimer's cases (OR = 0.40, p = 0.004).

## Methods used
HiC, chromatin conformation capture (Capture-C), single-nucleus multiomics (RNA-seq and ATAC-seq), bulk ATAC-seq, and ChIP-seq for H3K27Ac and CTCF.

## Method and dataset
Utilized HiC and other genomics methods to analyze cCREs in neural progenitor cells and neurons differentiated from human iPSC cultures; focused on genetic variation linked to MAPT expression.

## Limitations
The study primarily focuses on a subset of candidate regulatory elements and may not comprehensively account for all functional regulatory regions affecting MAPT expression.

## Evidence pattern
entity_definition, validation

## Extends or contradicts
This study contradicts typical interpretations of genetic risk factors in Alzheimer's by suggesting that some enhancer disruptions may be protective.

## Boundary conditions
Works when: Works when analyzing genetic variation in large datasets of differentiated neurons to assess enhancer activity.
Fails when: May not apply to undifferentiated cells or datasets lacking comprehensive genomic annotation.
