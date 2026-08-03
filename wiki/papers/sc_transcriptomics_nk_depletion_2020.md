---
paper_id: sc_transcriptomics_nk_depletion_2020
title: "Single-cell transcriptomics of blood reveals a natural killer cell subset depletion in tuberculosis."
doi: "10.1016/j.ebiom.2020.102686"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC7047188/"
source_ids: {doc_id: "pmc:7047188", pmid: "32114394", pmcid: "", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_clustering", "rna_cell_type_annotation", "rna_differential_abundance"]
retrieval_goals: ["prior_findings"]
retrieval_intents: ["What are canonical PBMC cell type and subtype marker genes to expect in human PBMC scRNA-seq?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
This study performed 10x Genomics single-cell RNA-seq on human PBMCs from healthy controls, latent TB infection (LTBI) and active TB patients, identifying 29 transcriptionally distinct PBMC subsets and marker genes. It reports progressive depletion of a CD3− CD7+ GZMB+ NK subset in LTBI and active TB, validated by flow cytometry in independent cohorts and partially restored after anti-TB therapy, suggesting a peripheral-blood biomarker for active TB.

## Hypothesis framed
Mycobacterium tuberculosis infection alters peripheral blood PBMC subset composition and specific transcriptionally defined subsets (notably a CD3− CD7+ GZMB+ NK population) are depleted in active TB and can serve as peripheral biomarkers distinguishing TB from LTBI and healthy states.

## Questions answered
- Which PBMC subsets differ in frequency between healthy controls, latent TB infection, and active TB?
- Is there an NK subset depleted in active TB that can discriminate active TB from LTBI and healthy controls?
- Does anti-TB treatment restore the frequency of the depleted NK subset?

## Key findings
Discovery scRNA-seq (7 donors, ~62,628 QC cells) resolved three major PBMC compartments and 29 subclusters with cluster-specific markers. A specific NK subset defined by CD3− CD7+ GZMB+ was progressively depleted across HC → LTBI → TB. Flow-cytometry validation in independent cohorts (cohort2: HC n=81, TB n=50; cohort3: HC n=39, LTBI n=27, TB n=37) confirmed depletion in TB and showed increased frequency of this subset after anti-TB treatment. Additional novel subset marker genes reported include IFITM1, GIMAP7, BANK1, and FCN1.

## Methods used
10x Genomics single-cell RNA-seq on PBMCs; Seurat unsupervised clustering; tSNE visualization; differential gene expression to define cluster markers; flow cytometry validation on independent cohorts; routine blood counts; longitudinal sampling of treated patients.

## Method and dataset
10x Genomics 3' scRNA-seq on PBMCs from a discovery cohort of 7 donors (2 HC, 2 LTBI, 3 TB) yielding ~62,628 high-quality single-cell profiles after QC. Analysis used Seurat clustering and tSNE; differential expression to define cluster markers. Validation performed by flow cytometry in larger cohorts (cohort2: HC n=81, TB n=50; cohort3: HC n=39, LTBI n=27, TB n=37) including longitudinal samples post-treatment. Assumes peripheral blood PBMC composition reflects disease-associated systemic immune changes and that transcript counts capture marker expression.

## Limitations
Small scRNA-seq discovery cohort (n=7) limiting generalisability and statistical power; predominantly cross-sectional sampling with limited longitudinal follow-up; peripheral blood profiling may not reflect tissue-resident lung immune responses; no functional assays to characterize the depleted NK subset (mechanism unknown); potential batch effects and clinical heterogeneity despite validation.

## Evidence pattern
entity_definition (cluster-level marker genes), comparison_design (HC vs LTBI vs TB), statistical_unit (single cells and donor-level cohorts), metric (subset frequency, differential gene expression), covariates (clinical group, treatment status; routine blood counts compared), validation (flow cytometry in independent cohorts and longitudinal samples), boundary_conditions (peripheral blood PBMC, 10x scRNA-seq), analysis_used (Seurat clustering, tSNE, differential expression).

## Extends or contradicts
Extends prior observations that circulating immune-cell subset composition is altered in TB by providing single-cell resolution and identifying a specific CD3− CD7+ GZMB+ NK subset depleted in LTBI and active TB, and by validating frequency changes by flow cytometry.

## Boundary conditions
Works when: Human peripheral blood PBMC profiled with 10x Genomics scRNA-seq or flow cytometry; cohorts include healthy controls, LTBI and active TB; sample sizes comparable to validation cohorts (tens of donors per group for validation); marker genes/transcripts (CD7, GZMB) are detectable by the chosen assay; cluster resolution sufficient to resolve 20–30 subclusters.
Fails when: Applied to tissue-resident immune cells (e.g., lung) rather than peripheral blood; discovery cohort sizes much smaller than used here (<<7 donors) without validation; assays/platforms that poorly capture GZMB or CD7 transcripts/proteins; when functional role or causality of the NK subset is required (no functional characterization provided).
