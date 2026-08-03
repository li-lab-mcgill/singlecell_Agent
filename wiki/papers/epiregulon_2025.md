---
paper_id: epiregulon_2025
title: "Epiregulon: Single-cell transcription factor activity inference to predict drug response and drivers of cell states."
doi: "10.1038/s41467-025-62252-5"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12318008/"
source_ids: {doc_id: "pmc:12318008", pmid: "40753156", pmcid: "12318008", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multi_grn_inference", "atac_grn_inference", "atac_motif_analysis"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Map method classes for TF activity and regulatory network inference from single-cell multiome data and identify their assumptions/failure modes."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
Epiregulon is a computational method for inferring single-cell transcription factor and transcriptional coregulator activity from paired scRNA-seq and scATAC-seq data by combining regulator expression with chromatin accessibility at TF binding sites in each cell. The paper evaluates Epiregulon in perturbation and drug-response settings, including androgen receptor inhibition, androgen receptor degradation, SMARCA4 degradation, lineage reprogramming, and tumorigenesis.

## Hypothesis framed
Integrating regulator expression with chromatin accessibility at regulator binding sites in individual cells will infer transcription factor and coregulator activity more accurately than regulator mRNA expression alone and will improve prediction of drug responses and cell-state drivers.

## Questions answered
- Does co-occurrence of TF expression and chromatin accessibility at TF binding sites improve single-cell transcriptional regulator activity inference compared with TF expression alone?
- Can Epiregulon predict the effects of androgen receptor inhibition across an AR antagonist and an AR degrader?
- Can ChIP-seq-informed regulatory networks infer activity for transcriptional coregulators or neomorphic TF programs better than motif-annotation-based networks?

## Key findings
Epiregulon inferred transcriptional regulator activity more accurately than approaches relying only on TF expression. It predicted effects of androgen receptor inhibition across both an AR antagonist and an AR degrader, identified context-dependent interaction partners for a SMARCA4 degrader, and prioritized candidate drivers of lineage reprogramming and tumorigenesis. ChIP-seq-informed regulatory networks outperformed motif-annotation-based approaches, including motif predictions prioritized by deep learning models.

## Methods used
Construction of gene regulatory networks from paired single-cell RNA-seq and ATAC-seq data using motif annotations or ChIP-seq-derived regulator binding information; single-cell regulator activity scoring from co-occurrence of regulator expression and accessibility at target regulatory elements; pruning and weighting of regulatory networks; differential regulator activity analysis; perturbation and drug-response validation for AR inhibition, AR degradation, and SMARCA4 degradation.

## Method and dataset
Epiregulon was applied to paired scRNA-seq and scATAC-seq datasets, with optional ChIP-seq-derived binding information for motif-agnostic regulator activity inference. Dataset sizes are not provided in the summary. The method assumes paired RNA and ATAC measurements per cell, detectable regulator expression, accessible regulatory elements linked to target genes or regulatory targets, and either motif annotations or relevant ChIP-seq binding profiles.

## Limitations
Epiregulon depends on the availability and quality of paired single-cell RNA-seq and ATAC-seq data. Accuracy may be limited by sparse RNA or ATAC measurements, insufficient representation of relevant cell states, batch effects, incomplete regulatory annotations, incomplete peak-to-gene or regulator-to-target information, and lack of relevant or context-matched ChIP-seq datasets. Computational predictions of regulator activity and candidate drivers require experimental validation.

## Evidence pattern
The paper supports its claims through entity definition of Epiregulon, comparison of activity inference against TF-expression-based approaches, validation in perturbation and drug-response contexts, comparison of ChIP-seq-informed versus motif-annotation-based regulatory networks, and boundary-condition analysis contrasting motif-based inference with motif-agnostic ChIP-seq-informed inference.

## Extends or contradicts
This paper extends gene regulatory network and transcription factor activity inference approaches that rely on gene expression or motif annotations by adding single-cell co-occurrence of regulator expression and chromatin accessibility, and by incorporating ChIP-seq data for coregulators, motif-lacking regulators, and neomorphic regulator programs.

## Boundary conditions
Works when: Works when paired scRNA-seq and scATAC-seq are available for the same cells, regulator mRNA is measured, TF binding sites or ChIP-seq-derived binding profiles are available, and the biological context includes accessible regulatory elements informative of regulator activity. ChIP-seq-informed inference is especially applicable when the regulator lacks a DNA-binding motif, is a chromatin remodeler or coregulator, or has altered binding due to mutation or context-dependent cofactors.
Fails when: May fail or degrade when only RNA-seq or only ATAC-seq is available, when paired multiome data are too sparse to detect co-occurrence of expression and accessibility, when relevant binding sites are absent or incorrectly annotated, when ChIP-seq data are unavailable or not matched to the cellular context, when rare cell states are poorly sampled, or when batch effects obscure expression-accessibility relationships.
