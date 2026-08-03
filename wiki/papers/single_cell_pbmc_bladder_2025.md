---
paper_id: single_cell_pbmc_bladder_2025
title: "Single-cell analysis reveals potential therapeutic markers of peripheral blood mononuclear cells from bladder cancer patients."
doi: "10.1590/1414-431X2025e14002"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12068768/"
source_ids: {doc_id: "pmc:12068768", pmid: "40367012", pmcid: "12068768", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_clustering", "rna_cell_type_annotation", "rna_differential_abundance"]
retrieval_goals: ["prior_findings"]
retrieval_intents: ["Find a PBMC atlas or review listing canonical marker genes per major immune cell type and subsets."]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
Single-cell RNA-seq of 44,022 PBMCs from four treatment‑naive bladder cancer patients and healthy donors produced a high-resolution atlas of circulating immune subsets, identified altered cell-type proportions (increased T cells and neutrophils), and nominated circulating immune checkpoints (e.g., LAG3, TIM-3) and cell-type–specific marker signatures as candidate therapeutic targets or biomarkers in bladder cancer.

## Hypothesis framed
Peripheral blood mononuclear cells from bladder cancer patients exhibit altered cell-type composition and increased expression of inhibitory checkpoint markers compared to healthy donors, enabling identification of circulating therapeutic targets and biomarkers.

## Questions answered
- Do PBMCs from bladder cancer patients show altered immune cell-type proportions compared to healthy donors?
- Which circulating PBMC subpopulations express immune checkpoint or inhibitory receptor genes that could serve as therapeutic targets or biomarkers in bladder cancer?
- Are there circulating monocyte or neutrophil subsets associated with pro-tumor pathways (e.g., hypoxia, angiogenesis) in bladder cancer patients?

## Key findings
Analyzed 44,022 PBMCs (33,816 patient cells; 10,206 healthy cells). Patients had increased proportions of T cells and neutrophils versus healthy donors. Created annotated clusters for T, NK, B, monocyte, DC and neutrophil populations, including seven CD8 and three CD4 clusters. CD8-T2-GZMK cells from patients showed elevated LAG3, HAVCR2 (TIM-3), and CTLA4 expression (exhausted phenotype); LAG3 and TIM-3 nominated as candidate checkpoints. CD8-T7-STMN1 cells highly expressed ITGAE, CD38, and STMN1. NK3-CMC1 (enriched in patients) highly expressed TIGIT. Bcell2-TCL1A and Bcell3-MS4A1 expressed inhibitory receptor markers consistent with tumor-associated phenotypic shifts. Mono4-THBS1 was associated (GSVA) with hypoxia and angiogenesis pathways and proposed as a source of tumor-enriched monocyte-like cells. Neu-FCGR3B neutrophils expressed IL4R and CD274 (PD-L1), suggested as detrimental to anti-tumor responses and a potential predictive marker.

## Methods used
Single-cell RNA sequencing of PBMCs; quality control (feature count and mitochondrial percent filters, doublet removal) and normalization in Seurat; clustering and manual annotation using canonical markers; T-cell re-clustering into CD4/CD8 subtypes; differential cluster abundance testing; marker gene identification/differential expression per cluster; gene set variation analysis (GSVA) for pathway inference; integration/validation using two external 10x healthy-donor PBMC datasets.

## Method and dataset
Seurat-based scRNA-seq analysis applied to PBMC transcriptomes (44,022 cells total: 33,816 from four treatment‑naive bladder cancer patients collected prior to surgery; 10,206 from one primary healthy donor plus two external 10x healthy datasets). Experimental design: cross-sectional case (patients) vs control (healthy donors) comparison. Assumptions include adequate QC filtering (mitochondrial %, feature counts), reliable cluster annotation using canonical markers, and that GSVA pathway scores on PBMC data reflect functional pathway enrichment.

## Limitations
Small cohort size (four patients and one primary healthy donor; two external healthy datasets added) limiting generalizability; analysis restricted to peripheral blood without paired tumor microenvironment or longitudinal sampling; observational cross-sectional design prevents causal inference; no functional or clinical validation of nominated targets; potential batch effects from integrating external datasets.

## Evidence pattern
entity_definition, statistical_unit, comparison_design, effect_metric, controls_covariates, validation, boundary_conditions; analyses used: clustering, cluster annotation, differential abundance, marker gene expression testing, GSVA

## Extends or contradicts
Extends prior observations that immune checkpoint/exhaustion markers are relevant for cancer immunotherapy by identifying LAG3 and TIM-3 expression in circulating CD8-T2-GZMK cells and nominating additional circulating inhibitory-marker–expressing subsets (NK3-CMC1, Bcell2-TCL1A, Bcell3-MS4A1, Neu-FCGR3B) in bladder cancer.

## Boundary conditions
Works when: Applies to cross-sectional scRNA-seq PBMC datasets from treatment‑naive bladder cancer patients and healthy donors with total cell counts on the order of tens of thousands (here 44k cells), where QC filtering (feature counts, mitochondrial percent, doublet removal) and Seurat-based normalization/clustering are used and external 10x healthy controls are available for integration.
Fails when: Does not apply when sample sizes are much smaller (e.g., <1,000 cells per group) or patient cohorts differ (treated patients, non-bladder cancers), when tumor microenvironment samples are required to infer intratumoral phenotypes, when longitudinal or functional validation is needed to establish causality, or when strong uncorrected batch effects/technical confounders prevent reliable cluster annotation.
