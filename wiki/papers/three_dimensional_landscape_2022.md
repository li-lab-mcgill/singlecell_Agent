---
paper_id: three_dimensional_landscape_2022
title: "The three-dimensional landscape of cortical chromatin accessibility in Alzheimer's disease."
doi: "10.1038/s41593-022-01166-7"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9581463/"
source_ids: {doc_id: "pmc:9581463", pmid: "36171428", pmcid: "9581463", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_differential_accessibility", "atac_peak_to_gene", "atac_grn_inference"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["Learn what prior single-cell chromatin or multiome studies have shown about AD-associated CREs, enhancer accessibility, and cell-type-specific genetic risk in human brain."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study generated 636 ATAC-seq libraries from fluorescence-sorted neuronal and non-neuronal nuclei from superior temporal gyrus and entorhinal cortex of 153 Alzheimer's disease cases and 56 controls. It mapped open chromatin regions, inferred enhancer-promoter interactions and cis-regulatory domains, and tested how chromatin accessibility, 3D regulatory organization, and transcription factor networks are altered in Alzheimer's disease.

## Hypothesis framed
Alzheimer's disease is associated with cell-type- and brain-region-specific disruptions of cortical chromatin accessibility that affect enhancer-promoter regulation, 3D cis-regulatory domains, transcription factor networks, and gene-expression programs.

## Questions answered
- Which neuronal and non-neuronal open chromatin regions in superior temporal gyrus and entorhinal cortex are associated with Alzheimer's disease phenotypes?
- Can interindividual variability in ATAC-seq accessibility be used to infer cis-regulatory domains that reflect 3D genome organization in human cortex?
- Do Alzheimer's disease-associated accessibility changes implicate specific transcription factor networks, including USF2-regulated lysosomal genes?

## Key findings
The study identified 315,630 neuronal and 205,120 non-neuronal open chromatin regions, including 50,836 regions not previously annotated. Chromatin accessibility explained a large fraction of gene-expression variation, and cell-type-specific enhancer-promoter interactions were identified for more than half of protein-coding genes. Interindividual accessibility variation was sufficient to infer cis-regulatory domains corresponding to 3D genome organization. Alzheimer's disease was associated with altered chromatin accessibility, altered 3D regulatory domains, and disrupted transcription factor networks; USF2 was one of the most AD-perturbed transcription factors, and experimental validation supported its regulation of lysosomal genes.

## Methods used
Fluorescence sorting of NeuN-positive neuronal and NeuN-negative non-neuronal nuclei from postmortem human cortex; ATAC-seq library generation; open chromatin region calling; cell-type-stratified accessibility analysis; integration with matched RNA-seq and additional epigenomic data; computational enhancer-promoter interaction inference; cis-regulatory domain inference from interindividual accessibility covariance; association testing against Alzheimer's disease case-control status, Braak stage, neuritic plaque density, and clinical dementia rating; transcription factor regulatory network analysis; experimental validation of USF2 effects on lysosomal genes.

## Method and dataset
The dataset consisted of 636 bulk ATAC-seq libraries from sorted neuronal and non-neuronal nuclei isolated from superior temporal gyrus and entorhinal cortex of 153 Alzheimer's disease cases and 56 controls, producing approximately 19.6 billion read pairs. The design compared accessibility across disease status and AD-related phenotypes while stratifying by broad cell compartment and brain region. Enhancer-promoter and cis-regulatory-domain analyses assume that interindividual covariance in accessibility reflects shared regulatory architecture and 3D genome organization, and that sorted NeuN-positive and NeuN-negative nuclei provide meaningful neuronal versus non-neuronal regulatory profiles.

## Limitations
The study used postmortem human brain tissue, so results may be affected by agonal state, postmortem interval, tissue preservation, medication exposure, and other donor-related variables. NeuN-positive and NeuN-negative sorting captures broad neuronal and non-neuronal compartments but does not resolve microglia, astrocytes, oligodendrocytes, OPCs, inhibitory and excitatory neuronal subtypes, or other fine cell populations. Enhancer-promoter links and cis-regulatory domains were largely computationally inferred and require additional experimental validation. The observational design limits causal interpretation of AD-associated chromatin changes. The cohort came from a specific brain bank and focused on superior temporal gyrus and entorhinal cortex, so findings may not generalize to all populations, disease stages, or brain regions.

## Evidence pattern
Entity definition: defined neuronal and non-neuronal cortical open chromatin regions, enhancer-promoter interactions, cis-regulatory domains, and AD-perturbed transcription factor networks. Comparison design: compared 153 AD cases with 56 controls and tested associations with Braak stage, neuritic plaque density, and clinical dementia rating. Statistical unit: ATAC-seq libraries generated from sorted postmortem nuclei by donor, brain region, and cell compartment. Metrics: chromatin accessibility levels, open chromatin region catalogs, enhancer-promoter interaction calls, cis-regulatory domain structure, gene-expression variation explained, and transcription factor perturbation scores. Covariates and controls: disease-control comparisons and AD-related phenotype associations were performed in human postmortem samples with quality control, although exact covariates are not specified in the supplied summary. Validation: USF2 regulatory effects on lysosomal genes were experimentally evaluated. Boundary conditions: evidence applies to sorted neuronal and non-neuronal nuclei from superior temporal gyrus and entorhinal cortex rather than single-nucleus cell-subtype-resolved or same-cell multiome data.

## Extends or contradicts
This paper extends prior human brain regulatory-element studies by expanding the catalog of cortical open chromatin regions and linking Alzheimer's disease-associated accessibility changes to inferred enhancer-promoter interactions, cis-regulatory domains, and transcription factor networks. No direct contradiction of a specified prior wiki paper is supported by the supplied summary.

## Boundary conditions
Works when: The approach is applicable to large cohorts of postmortem brain ATAC-seq data with many donors, sorted or otherwise stratified cell compartments, matched or integrable gene-expression data, and enough interindividual accessibility variation to estimate enhancer-promoter relationships and cis-regulatory domains. The reported findings specifically apply to NeuN-positive neuronal and NeuN-negative non-neuronal nuclei from superior temporal gyrus and entorhinal cortex in Alzheimer's disease and control donors.
Fails when: The study does not provide true single-nucleus cell-subtype resolution and is not suitable for assigning AD accessibility effects to microglia, astrocytes, oligodendrocytes, OPCs, or neuronal subtypes. It does not provide same-cell multiome linkage between chromatin accessibility and gene expression. It provides limited direct evidence in the supplied summary for AD GWAS variant enrichment, fine-mapping, or variant-to-enhancer-to-gene assignment. Causal claims are limited because the design is observational and based on postmortem tissue.
