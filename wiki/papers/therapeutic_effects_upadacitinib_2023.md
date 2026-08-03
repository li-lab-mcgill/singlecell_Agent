---
paper_id: therapeutic_effects_upadacitinib_2023
title: "Therapeutic Effects of Upadacitinib on Experimental Autoimmune Uveitis: Insights From Single-Cell Analysis."
doi: "10.1167/iovs.64.12.28"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC10506681/"
source_ids: {doc_id: "pmc:10506681", pmid: "37713206", pmcid: "10506681", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_motif_analysis", "atac_cell_type_annotation", "multiomic_integration"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["Summarize lineage-defining TF motif and accessibility patterns in human PBMC scATAC-seq"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
This study uses scRNA-seq and scATAC-seq on PBMCs from 12 VKH patients and on cervical draining lymph node (CDLN) cells from a mouse EAU model to show JAK/STAT pathway upregulation in uveitis and demonstrate that the JAK1-selective inhibitor upadacitinib reduces disease severity, suppresses pathogenic CD4 T cell programs, increases Treg frequency, and normalizes aberrant cell–cell communication including a CXCR4-mediated migration axis.

## Hypothesis framed
Inhibition of JAK1 with upadacitinib will reduce autoimmune uveitis severity by reversing JAK/STAT-associated chromatin and transcriptional programs in disease-associated immune cell subsets and by normalizing pathogenic intercellular communication networks (e.g., CXCR4-mediated migration).

## Questions answered
- Is the JAK/STAT pathway transcriptionally and chromatin-level upregulated in PBMCs from VKH patients and in CDLN cells from mouse EAU?
- Does JAK1-selective inhibition with upadacitinib reduce EAU clinical and histologic severity and alter pathogenic CD4 T cell proliferation/signatures while increasing Treg frequency?
- Does upadacitinib treatment and/or CXCR4 blockade normalize aberrant cell–cell communication (notably CXCR4-mediated migration) implicated in EAU?

## Key findings
1) scRNA-seq and scATAC-seq show increased JAK/STAT pathway activity and STAT-related chromatin signatures in PBMCs from 12 VKH patients versus 12 controls and across B cells, CD4 and CD8 T cells, and myeloid cells in EAU CDLN. 2) Upadacitinib treatment in IRBP1–20-induced EAU mice reduced clinical and histopathologic scores, decreased JAK1 protein expression (validated by western blot/flow cytometry), suppressed proliferation and pathogenic transcriptional programs in CD4 T cells while increasing Treg frequency, and reduced proportions of ISG15+ CD4 and CD8 T cells and B cells. 3) Upadacitinib downregulated inflammatory gene programs (IL-17, TNF, IFN-related genes) and reduced aberrant intercellular communication, notably inhibiting a CXCR4-mediated migration axis; pharmacologic CXCR4 inhibition independently showed therapeutic benefit in the model.

## Methods used
Single-cell RNA-seq and single-cell ATAC-seq on human PBMCs (VKH patients and controls) and mouse CDLN cells, integration of scRNA and scATAC data, differential gene expression and pathway enrichment analyses, cell–cell communication inference, flow cytometry, western blot, EAU induction in C57BL/6J mice with IRBP1–20 + pertussis toxin, clinical fundus photography and histology scoring, pharmacologic CXCR4 inhibition experiments.

## Method and dataset
Paired/unpaired scRNA-seq and scATAC-seq profiling of human PBMCs from 12 Vogt–Koyanagi–Harada (VKH) patients and 12 healthy controls, and scRNA/scATAC (CDLN) from IRBP1–20-induced EAU mice (C57BL/6J) with and without upadacitinib treatment; analyses assume standard scATAC peak calling and motif enrichment (interpreting motif accessibility as proxy for TF activity), integration assumes comparable cell-type annotations across samples and species, and validation performed by flow cytometry and western blot. Exact per-sample cell counts and peak matrices are not reported in the summary.

## Limitations
Small human cohort (n=12 patients, n=12 controls); reliance on mouse EAU model that may not fully replicate human disease or predict clinical dosing/safety; limited direct mechanistic perturbations beyond pharmacologic CXCR4 blockade; no comprehensive lineage-defining motif tables or downloadable peak-by-cell matrices reported; long-term effects and potential off-target effects of upadacitinib not assessed.

## Evidence pattern
entity_definition, comparison_design, statistical_unit, effect_metric, covariates, validation, boundary_conditions

## Extends or contradicts
Extends prior reports that dysregulated JAK/STAT signaling is implicated in autoimmune uveitis by adding single-cell chromatin (scATAC-seq) and transcriptomic evidence and by demonstrating in vivo therapeutic effects of a JAK1-selective inhibitor; does not report contradictions to previous findings.

## Boundary conditions
Works when: Applies to PBMC scATAC/scRNA profiling from VKH patients (n=12) versus matched controls and to CDLN cells from IRBP1–20-induced EAU in C57BL/6J mice; detection of JAK/STAT activation at chromatin and RNA levels requires multiomic single-cell data and downstream validation (flow cytometry/western blot); therapeutic effects observed under the EAU induction protocol and dosing/regimen used in the mouse experiments.
Fails when: Findings may not generalize when sample size is smaller than studied cohorts (human n=12), in uveitis etiologies not driven by JAK/STAT signaling, in species or models that do not recapitulate JAK1-dependent mechanisms, when only bulk ATAC/RNA data are available (no single-cell resolution), or without orthogonal validation of protein expression/cell phenotypes.
