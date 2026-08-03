---
paper_id: znf683_marks_cd8_tcells_2023
title: "ZNF683 marks a CD8 + T cell population associated with anti-tumor immunity following anti-PD-1 therapy for Richter syndrome."
doi: "10.1016/j.ccell.2023.08.013"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC10618915/"
source_ids: {doc_id: "pmc:10618915", pmid: "37738974", pmcid: "10618915", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_cell_type_annotation", "rna_trajectory", "rna_grn_inference"]
retrieval_goals: ["prior_findings"]
retrieval_intents: ["What are canonical PBMC cell type and subtype marker genes to expect in human PBMC scRNA-seq?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
The study uses single-cell RNA-seq and paired TCR-seq on longitudinal bone marrow samples from Richter syndrome patients treated with nivolumab plus ibrutinib to identify a ZNF683-high CD8+ intermediate exhausted effector/effector-memory population associated with clinical response to PD-1 blockade. It maps ZNF683 targets (CUT&RUN, bulk RNA-seq) and validates associations in pre-treatment peripheral blood from an independent RS cohort and in datasets from PD-1–responsive solid tumors.

## Hypothesis framed
ZNF683-high CD8+ T cells define an intermediate exhausted effector/effector-memory population that is associated with and functionally contributes to anti-tumor responses following PD-1 blockade in Richter syndrome.

## Questions answered
- Which CD8+ T cell subset(s) in Richter syndrome associate with clinical response to anti-PD-1 therapy?
- Does ZNF683 define a transcriptionally and clonally distinct intermediate exhausted CD8+ population that originates from TCF7+ stem-like memory cells and is distinct from terminally exhausted TOX+/EOMES+/BLIMP1+ cells?
- Is a pre-treatment peripheral blood ZNF683-high T cell signature associated with response to anti-PD-1 in independent RS and solid tumor cohorts?

## Key findings
Analyzed 17 longitudinal bone marrow samples from 6 RS patients (4 responders, 2 non-responders). Identified an intermediate exhausted CD8 effector/effector-memory population with high ZNF683 expression that is associated with clinical response to PD-1 blockade. Trajectory and clonotype analyses indicate ZNF683-high cells evolve from TCF7+ stem-like memory cells and are transcriptionally distinct from terminally exhausted (TOX+, EOMES+, BLIMP1+) cells. CUT&RUN and bulk RNA-seq show ZNF683 directly targets T cell genes including TCF7, LMO2, and CD69 and influences cytotoxicity/activation pathways. Signature overlap observed with tumor-infiltrating populations from anti-PD-1–responsive solid tumors. Pre-treatment peripheral blood ZNF683-high T cell signatures associate with response in an independent RS cohort (n=10) and in external solid tumor datasets.

## Methods used
Single-cell RNA sequencing, paired T cell receptor (TCR) sequencing, FACS-based separation of malignant vs non-malignant fractions, clustering, trajectory analysis, clonotype lineage analysis, CUT&RUN to map ZNF683 binding, bulk RNA-seq in cell lines for target validation, signature overlap analyses with external datasets, validation using pre-treatment peripheral blood RNA-seq.

## Method and dataset
scRNA-seq + paired TCR-seq on 17 bone marrow samples collected longitudinally from 6 RS patients treated with nivolumab plus ibrutinib (4 responders, 2 non-responders) with FACS separation of fractions; CUT&RUN and bulk RNA-seq performed in cell lines to map ZNF683 targets; validation using pre-treatment peripheral blood bulk RNA-seq from an independent RS cohort (n=10) and public datasets of PD-1–treated solid tumors. Assumes bone marrow samples capture relevant tumor immune microenvironment and that clonotype sharing and trajectory inference reflect lineage relationships.

## Limitations
Small discovery cohort (6 patients, 17 samples) limiting statistical power and generalizability. Patients received combination therapy (nivolumab + ibrutinib), confounding attribution solely to PD-1 blockade. Functional causality of ZNF683 in human anti-tumor responses not fully established and limited in vivo validation. Bone marrow sampling may not represent all tumor microenvironments. Some validation datasets require controlled access.

## Evidence pattern
entity_definition (ZNF683-high CD8 intermediate exhausted cells), trajectory and clonotype lineage analyses, CUT&RUN and bulk RNA-seq functional target mapping, validation in independent peripheral blood cohort (n=10) and external solid tumor datasets; controlled comparison between responders and non-responders; patient-level and cell-level analyses with covariate considerations (treatment regimen).

## Extends or contradicts
Extends prior characterization of heterogeneous T cell exhaustion programs by identifying a ZNF683-high intermediate exhausted CD8 population that evolves from TCF7+ stem-like cells and is distinct from TOX+/EOMES+/BLIMP1+ terminally exhausted cells; aligns with reports of TCF7+ stem-like and reinvigoratable CD8+ T cell populations in PD-1–responsive tumors.

## Boundary conditions
Works when: Applied to scRNA-seq (with paired TCR where available) from Richter syndrome bone marrow or peripheral blood of patients treated with PD-1 blockade (here nivolumab ± ibrutinib); when ZNF683 expression is detectable in CD8+ T cells; when dataset size and depth permit clustering, trajectory and clonotype analyses (example: 17 samples from 6 patients plus validation cohorts). Signature-based validation requires bulk or single-cell expression data from pre-treatment peripheral blood or tumor-infiltrating lymphocytes.
Fails when: Findings may not apply when patients are untreated or treated with different regimens (no PD-1 blockade), in other hematologic malignancies or non-bone-marrow tissues without validation, when sample sizes are too small or sequencing depth insufficient to resolve CD8+ subpopulations, when ZNF683 expression is absent or extremely low, or when paired TCR/CUT&RUN data are not available to support lineage/target claims. Causal inference is not supported in cohorts receiving combination therapy without isolated PD-1 blockade arms.
