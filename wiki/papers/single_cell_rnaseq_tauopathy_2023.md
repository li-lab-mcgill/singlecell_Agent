---
paper_id: single_cell_rnaseq_tauopathy_2023
title: "Single-cell RNA-seq reveals alterations in peripheral CX3CR1 and nonclassical monocytes in familial tauopathy."
doi: "10.1186/s13073-023-01205-3"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC10354988/"
source_ids: {doc_id: "pmc:10354988", pmid: "37464408", pmcid: "", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_cell_type_annotation", "rna_differential_abundance", "rna_differential_expression"]
retrieval_goals: ["prior_findings"]
retrieval_intents: ["What are canonical PBMC cell type and subtype marker genes to expect in human PBMC scRNA-seq?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
The study performed single-cell RNA-seq profiling of ~181,000 PBMCs from 8 carriers of pathogenic MAPT variants and 8 matched non-carrier controls, identifying cell-type-specific transcriptional and compositional alterations associated with familial tauopathy. Key validated findings include reduced CX3CR1 expression in monocytes and NK cells and decreased circulating nonclassical (FCGR3A+/CD16+) monocytes, suggesting peripheral immune alterations linked to tau pathology and candidate peripheral biomarkers.

## Hypothesis framed
Carriers of pathogenic MAPT variants exhibit altered peripheral blood immune cell composition and cell-type-specific gene expression—specifically reduced CX3CR1 expression and decreased nonclassical monocyte abundance—relative to matched non-carrier controls.

## Questions answered
- Do carriers of pathogenic MAPT variants have altered PBMC cell-type composition compared with matched non-carrier controls (e.g., reduced nonclassical monocytes)?
- Are CX3CR1 and nonclassical monocyte marker genes (e.g., FCGR3A) differentially expressed in PBMCs of MAPT pathogenic-variant carriers?
- Can single-cell transcriptomic findings in MAPT carriers be validated by orthogonal assays (flow cytometry and ddPCR) and supported by external datasets?

## Key findings
Using scRNA-seq of ~181,000 PBMCs from 8 MAPT variant carriers and 8 matched controls, the authors found a marked reduction in circulating nonclassical (NC; FCGR3A+/CD16+) monocytes in MAPT carriers relative to controls (confirmed by flow cytometry, most apparent when normalized to conventional dendritic cells). They observed significant downregulation of CX3CR1 in monocytes and NK cells in MAPT carriers (replicated by ddPCR and supported by decreased Cx3cr1 in a MAPT P301S mouse microglia dataset). NC monocyte marker genes including FCGR3A were dysregulated (reduced), and TMEM176A and TMEM176B expression was reduced in peripheral myeloid cells.

## Methods used
Single-cell RNA sequencing of PBMCs (~181k cells), clustering and cell-type annotation, cell-type-specific differential gene expression, proportionality/differential abundance analyses (per-donor and cluster-normalized measures), flow cytometry for cell-type abundance validation, droplet digital PCR (ddPCR) for transcript validation, and secondary analyses of public transcriptomic datasets including a MAPT P301S mouse microglia dataset.

## Method and dataset
ScRNA-seq of human peripheral blood mononuclear cells: ~181,000 single-cell transcriptomes from 16 donors (8 carriers of diverse pathogenic MAPT variants across mixed clinical stages and 8 age- and sex-matched non-carrier controls). Analysis pipeline included clustering, annotation to canonical PBMC cell types, per-cell-type differential expression and proportionality analyses using per-donor aggregated measures; validations performed by flow cytometry and ddPCR. Assumptions: matched controls mitigate confounding by age/sex; per-donor and cluster-normalized statistics capture consistent group-level differences despite inter-donor heterogeneity.

## Limitations
Small sample size (n=8 carriers, n=8 controls) with heterogeneity of MAPT variants and clinical phenotypes limiting generalizability and power; cross-sectional design prevents causal or temporal inference; PBMCs have very low MAPT expression, so changes are likely indirect/systemic rather than cell-autonomous effects of mutant tau; validation targeted only a subset of genes and cell types; potential confounding by medications, comorbidities, and scRNA-seq technical/normalization biases.

## Evidence pattern
entity_definition, comparison_design, statistical_unit, controls_covariates, validation, boundary_conditions, analysis_used

## Extends or contradicts
Extends prior mouse-model evidence that CX3CR1 and fractalkine signaling modulate tau pathology and microglial responses by demonstrating reduced peripheral CX3CR1 expression and altered nonclassical monocyte abundance in human carriers of pathogenic MAPT variants.

## Boundary conditions
Works when: Applies to studies of familial MAPT pathogenic-variant carriers versus age- and sex-matched non-carrier controls profiled by PBMC scRNA-seq with per-donor aggregation (example here: 8 carriers, 8 controls, ~181k cells); findings validated when orthogonal assays (flow cytometry, ddPCR) are used and when proportionality analyses normalize NC monocytes to other myeloid populations such as cDCs.
Fails when: May not generalize to sporadic tauopathies, other MAPT variants or clinical stages not represented, cohorts with markedly different demographics or uncorrected confounders (medications, comorbidities), small-sample studies lacking orthogonal validation, tissue types other than peripheral blood (e.g., brain parenchyma), or experimental pipelines that do not use per-donor aggregation/cluster-normalized measures; cross-sectional data cannot establish temporal or causal relationships.
