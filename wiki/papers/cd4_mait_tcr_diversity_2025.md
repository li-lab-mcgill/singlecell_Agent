---
paper_id: cd4_mait_tcr_diversity_2025
title: "CD4+ mucosal-associated invariant T cells express highly diverse T cell receptors."
doi: "10.1093/jimmun/vkaf260"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12726071/"
source_ids: {doc_id: "pmc:12726071", pmid: "41206963", pmcid: "12726071", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_cell_type_annotation", "multi_cell_type_annotation"]
retrieval_goals: ["broad_background"]
retrieval_intents: ["Define MAIT cell RNA markers and expected chromatin/motif features in PBMC"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
Using MR1-5-OP-RU tetramer+ CD161++ cells from cryopreserved PBMCs of 13 healthy donors, the study applies spectral flow cytometry and unbiased single-cell V(D)J sequencing to define the TCR repertoire of CD4+ MAIT cells. It shows CD4+ MAITs are enriched for TRAV1-2−, highly diverse TCRs (including TRAV21, TRAV8 family, TRAV12 family) and that noncanonical TCRs are relatively increased after 7-day IL-2 + Mycobacterium tuberculosis lysate culture, suggesting alternative MR1 ligands may select these cells.

## Hypothesis framed
Human CD4+ MAIT cells use noncanonical (TRAV1-2−) TCRs distinct from canonical TRAV1-2+ CD8+ MAITs and therefore possess a more diverse TCR repertoire that may be selected by alternative MR1 ligands.

## Questions answered
- Are CD4+ MAIT cells enriched for TRAV1-2− (noncanonical) TCRs compared with canonical CD8+ TRAV1-2+ MAITs?
- Do CD4+ MAIT cells exhibit higher TCR diversity than TRAV1-2+ CD8+ MAITs?
- Are TRAV1-2− TCRs in MAITs enriched after in vitro culture with IL-2 and Mycobacterium tuberculosis lysate?

## Key findings
In MR1-5-OP-RU tetramer+ CD161++ cells from n=13 healthy donor PBMCs, CD4+ MAIT cells were enriched for TRAV1-2− TCRs and showed markedly higher TCRα/β diversity than TRAV1-2+ CD8+ MAITs. Noncanonical TRAV usages identified in CD4+ MAITs included TRAV21, TRAV8 family (TRAV8-1/2/3), and TRAV12 family (TRAV12-2/3) with more variable J segments, CDR3α sequences, and TRBV chains. Total MAIT populations expanded strongly to 5-OP-RU driven mainly by TRAV1-2+ CD8+ cells, whereas TRAV1-2− TCRs were relatively more frequent at baseline among CD4+ MAITs and were enriched after 7-day IL-2 + M. tuberculosis lysate culture.

## Methods used
Spectral flow cytometry with MR1-5-OP-RU tetramer and CD161 staining; single-cell unbiased V(D)J (TCRα/β) sequencing; stratification by CD4/CD8 and TRAV1-2 surface staining; in vitro 7-day cultures with IL-2 and stimuli (5-OP-RU, folate derivatives, anti-CD3/CD28, cytokines, M. tuberculosis lysate); comparative V(D)J repertoire analyses across two datasets.

## Method and dataset
Single-cell TCR V(D)J sequencing and spectral flow cytometry performed on MR1-5-OP-RU tetramer+ CD161++ cells sorted from cryopreserved PBMCs of 13 healthy donors; cells assayed fresh (baseline) and after 7-day in vitro stimulation with IL-2 and various antigens/agents. Assumptions include that MR1-5-OP-RU tetramer reliably defines MAITs (may bias toward 5-OP-RU reactive TCRs) and surface TRAV1-2 staining reflects TRAV1-2 usage.

## Limitations
Cohort limited to n=13 healthy donor peripheral blood—no tissue-resident or disease samples. Use of MR1-5-OP-RU tetramer and 5-OP-RU–based assays may bias detection toward 5-OP-RU–reactive/TRAV1-2+ cells and under-represent low-affinity TRAV1-2− cells. Noncanonical TCR antigen specificity was not functionally mapped to alternative MR1 ligands. In vitro expansion conditions (7-day IL-2 + stimuli) may not recapitulate in vivo selection. Sequencing depth, longitudinal sampling, and disease-context validation were limited.

## Evidence pattern
entity_definition; comparison_design; statistical_unit (donor-level and cell-level); controls and covariates (baseline vs 7-day cultures, TRAV1-2 staining); V(D)J repertoire analysis; in vitro stimulation assays; boundary_conditions documented.

## Extends or contradicts
Extends the canonical model that human MAIT cells predominantly express semi-invariant TRAV1-2 TCRs by demonstrating a distinct, private, and diverse TRAV1-2− TCR repertoire specifically enriched in CD4+ MAITs.

## Boundary conditions
Works when: Applied to MR1-5-OP-RU tetramer+ CD161++ cells from cryopreserved peripheral blood mononuclear cells of healthy adult donors (n≈13), analyzed by single-cell V(D)J sequencing and spectral flow; 7-day in vitro culture with IL-2 ± M. tuberculosis lysate for expansion assays.
Fails when: Does not apply to tissue-resident MAIT populations or disease-associated samples not represented in the cohort; findings may not hold when using MR1 tetramers loaded with ligands other than 5-OP-RU or when studying very low-affinity TRAV1-2− TCRs that fail tetramer staining; conclusions may not generalize for datasets with different sorting/selection (bulk TCR-seq) or shorter/longer in vitro culture conditions.
