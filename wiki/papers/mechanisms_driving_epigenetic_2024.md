---
paper_id: mechanisms_driving_epigenetic_2024
title: "Mechanisms driving epigenetic and transcriptional responses of microglia in a neurodegenerative lysosomal storage disorder model."
doi: "10.1101/2024.11.12.623296"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC11601307/"
source_ids: {doc_id: "pmc:11601307", pmid: "39605454", pmcid: "11601307", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_differential_expression", "atac_differential_accessibility", "atac_motif_analysis"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["Learn what prior single-cell or chromatin studies show about AD-associated cis-regulatory elements, enhancer-target gene links, TF programs, and non-coding AD risk localization by brain cell type."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study used Sgsh knockout mice, a model of Sanfilippo syndrome type A, to test how lysosomal dysfunction alters brain-cell transcriptional and epigenetic states. It found that microglia show the strongest disease-associated remodeling, with early dysregulation of lysosomal and immune genes and widespread activation of microglia-specific putative enhancers driven by MITF/TFE programs collaborating with PU.1/ETS and C/EBP factors.

## Hypothesis framed
Loss of Sgsh causes lysosomal stress that drives cell-type-specific transcriptional and enhancer remodeling in brain microglia, mediated by MITF/TFE transcription factors acting with PU.1/ETS and C/EBP factors.

## Questions answered
- Which major brain cell type shows the strongest phenotypic, transcriptional, and epigenetic response to Sgsh deficiency?
- Does Sgsh deficiency increase open chromatin and histone acetylation at microglia-specific enhancers linked to upregulated disease genes?
- Are MITF/TFE transcription factors implicated as drivers of lysosomal-stress-induced microglial transcriptional and enhancer activation programs?

## Key findings
Microglia were the major brain cell type with the most pronounced disease-associated alterations in Sgsh knockout mice. Microglial gene-expression changes began early in disease progression and involved lysosomal-function and immune-signaling pathways. Sgsh deficiency increased open chromatin and histone acetylation at thousands of putative microglia-specific enhancers associated with upregulated genes, while neurons and oligodendrocytes showed much smaller epigenetic effects. MITF/TFE family members were identified as context-dependent drivers of microglial epigenetic and transcriptional remodeling, acting with PU.1/ETS and C/EBP factors. Similar transcriptomic and epigenetic features were observed in microglia from mouse models of age-related neurodegeneration and human Alzheimer's disease patients.

## Methods used
Sgsh knockout mouse disease modeling; electron microscopy; immunohistochemistry; single-nucleus RNA-seq of major brain cell types; temporal microglial transcriptomic profiling; chromatin accessibility profiling; histone acetylation profiling; differential gene-expression analysis; differential chromatin-accessibility or enhancer-activation analysis; putative enhancer-to-gene association; transcription-factor motif and regulatory-program analysis; comparison to microglia from age-related neurodegeneration mouse models and human Alzheimer's disease patients.

## Method and dataset
The study analyzed brain tissue from Sgsh knockout mice versus controls across major brain cell types using imaging, single-nucleus RNA-seq, and epigenomic assays for open chromatin and histone acetylation. It included temporal profiling of microglial gene expression and comparison of microglial disease signatures to mouse age-related neurodegeneration models and human Alzheimer's disease patient data. Sample sizes, number of nuclei or cells, statistical thresholds, and exact assay platforms were not provided in the summary. The enhancer analyses assume that increased accessibility or histone acetylation marks putative active enhancers and that enhancer proximity or association with upregulated genes reflects regulatory linkage.

## Limitations
The summary does not report sample sizes, sex composition, statistical thresholds, exact disease-stage coverage, or the number of cells/nuclei analyzed. It does not describe direct localization of Alzheimer's disease GWAS variants or fine-mapped noncoding AD risk variants to the identified enhancers. Enhancer-target gene links appear to be putative rather than experimentally validated. Most mechanistic conclusions are based on mouse models and genomic association analyses, and causal effects of specific MITF/TFE, PU.1/ETS, or C/EBP perturbations on disease phenotypes require further in vivo validation. Translation to human MPS-IIIA and broader human neurodegenerative disease remains to be established.

## Evidence pattern
Entity definition: microglia, neurons, oligodendrocytes, and other major brain cell types were compared in Sgsh knockout and control mice. Comparison design: disease model versus control, with temporal microglial transcriptomic profiling and cross-disease comparison to age-related neurodegeneration mouse models and human Alzheimer's disease microglia. Analysis used: single-nucleus RNA-seq differential expression, chromatin accessibility and histone acetylation differential enhancer analysis, putative enhancer-gene association, and transcription-factor motif or regulatory-program analysis. Validation: imaging by electron microscopy and immunohistochemistry supported cellular phenotypic changes; overlap with mouse neurodegeneration models and human AD patients supported external relevance. Boundary conditions: conclusions are strongest for microglial responses to Sgsh-loss-induced lysosomal dysfunction, not for direct AD genetic risk localization.

## Extends or contradicts
This paper extends prior observations that disease-associated microglia occur in neurodegeneration by linking lysosomal dysfunction in Sgsh knockout mice to microglia-specific enhancer activation and MITF/TFE-centered transcription-factor programs. It does not directly contradict any specific existing wiki paper based on the provided summary.

## Boundary conditions
Works when: The findings apply to brain-cell profiling in Sgsh knockout mouse models of lysosomal storage disease, especially microglia undergoing lysosomal stress. The epigenetic interpretation applies when open chromatin and histone acetylation data can be assigned to brain cell types and compared between knockout and control conditions. The cross-disease relevance applies when comparing microglial transcriptomic or epigenetic disease programs across Sgsh deficiency, age-related neurodegeneration mouse models, and human Alzheimer's disease datasets.
Fails when: The study does not establish fine-mapped Alzheimer's disease risk variants, GWAS heritability enrichment, or noncoding AD risk localization in cell-type-specific enhancers. It is not sufficient to prove causal enhancer-target relationships or causal transcription-factor effects on disease phenotypes without perturbation experiments. Findings may not generalize to neurons or oligodendrocytes, which showed much smaller epigenetic effects, or to human MPS-IIIA without direct validation.
