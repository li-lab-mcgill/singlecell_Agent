---
paper_id: single_cell_iga_nephropathy_2021
title: "Single-cell RNA-sequencing reveals distinct immune cell subsets and signaling pathways in IgA nephropathy."
doi: "10.1186/s13578-021-00706-1"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC8665497/"
source_ids: {doc_id: "pmc:8665497", pmid: "34895340", pmcid: "8665497", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_clustering", "rna_cell_type_annotation", "rna_differential_expression"]
retrieval_goals: ["prior_findings"]
retrieval_intents: ["What are canonical PBMC cell type and subtype marker genes to expect in human PBMC scRNA-seq?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
This study used single-cell RNA-sequencing of peripheral blood mononuclear cells (PBMCs) from 10 newly diagnosed, treatment‑naive IgA nephropathy (IgAN) patients and 6 healthy controls to identify altered immune cell subsets and pathways in early IgAN. Key findings include reduced NK cell number and cytotoxic program, an IgAN-enriched B cell subset with suppressed NFκB signaling, an interferon-responsive monocyte subset associated with clinical severity, and widespread changes in inferred intercellular communications—findings validated in additional samples.

## Hypothesis framed
Early peripheral immune-cell transcriptomic programs and cell‑type abundances are altered in newly diagnosed, treatment‑naive IgA nephropathy patients compared with healthy controls and these alterations associate with clinical severity measures.

## Questions answered
- Which PBMC immune cell subsets and transcriptional programs differ between newly diagnosed, treatment‑naive IgAN patients and healthy controls?
- Are NK cell abundance and NK cell cytotoxicity-related transcriptional programs reduced in IgAN and do these measures correlate with clinical severity (UPCR, serum gd‑IgA1, serum IgA)?
- Is there a specific B cell or monocyte transcriptional subset enriched in IgAN that associates with disease progression or severity?

## Key findings
Using scRNA-seq of PBMCs from 10 IgAN patients and 6 healthy controls (16 samples total), the authors found: (1) NK cells showed significantly reduced abundance and downregulation of cytotoxicity-related transcriptional programs in IgAN; NK cell abundance and expression of NK marker genes negatively correlated with UPCR, serum galactose‑deficient IgA1, and serum IgA. (2) A distinctive B cell subset was enriched in IgAN, exhibited suppressed NFκB signaling, and its transcriptional signature was enriched for viral‑infection pathways; this B cell subset positively associated with measures of disease progression. (3) Classical monocytes had altered transcriptional states in IgAN and a monocyte subset with upregulated interferon‑induced genes correlated positively with clinical severity. (4) Inferred ligand–receptor intercellular communication networks were extensively rewired in IgAN PBMCs. Key results were confirmed in additional validation samples.

## Methods used
Single‑cell RNA sequencing of PBMCs, quality control filtering, unsupervised clustering, annotation of cell types/subsets, differential gene expression analysis between IgAN and control cells, pathway enrichment analysis, cell‑type abundance comparisons, correlation analyses between cell abundance/marker expression and clinical parameters (UPCR, serum gd‑IgA1, serum IgA), inference of ligand–receptor based intercellular communication networks, and validation in independent samples.

## Method and dataset
scRNA‑seq on peripheral blood mononuclear cells from 16 human subjects (10 newly diagnosed, treatment‑naive IgAN patients; 6 healthy controls) pooled across four multiplexed experiments. Analytical pipeline included QC filtering, clustering, marker identification and differential expression, pathway enrichment, cell‑type abundance testing, correlation with clinical measures, and ligand–receptor communication inference. Assumes that PBMC transcriptional profiles from cryopreserved samples and downstream normalization/batch correction faithfully reflect in vivo cell states.

## Limitations
Modest sample size from a single center (10 IgAN, 6 controls) and cross‑sectional design limit generalizability and causal inference; analysis restricted to PBMCs (no renal tissue single‑cell data), so tissue‑resident immune states and local interactions were not assessed; cryopreservation and batch effects may influence cell representation/transcriptional states despite QC; scRNA‑seq measures transcripts not protein or direct functional activity; mechanistic and longitudinal validation (functional assays, larger/diverse cohorts) lacking.

## Evidence pattern
entity_definition, comparison_design, statistical_unit, effect_metric, controls_covariates, validation, boundary_conditions

## Extends or contradicts
Extends prior models implicating immune responses and circulating gd‑IgA1 immune complexes in IgAN by providing single‑cell PBMC evidence for specific peripheral immune cell subset alterations (reduced NK cells, an IgAN‑enriched NFκB‑suppressed B cell subset, interferon‑active monocytes) and altered intercellular signaling; does not directly contradict prior findings.

## Boundary conditions
Works when: Applies to cross‑sectional comparisons of treatment‑naive, newly diagnosed IgAN patients versus healthy controls using scRNA‑seq of PBMCs processed with similar cryopreservation, multiplexing and QC/batch‑correction pipelines; cohort sizes on the order of ~10 cases and ~5–10 controls for discovery and small validation sets can detect cell‑type abundance and transcriptional program differences; clinical correlations tested with UPCR, serum gd‑IgA1 and serum IgA.
Fails when: Does NOT apply to tissue‑resident renal immune cells or analyses of kidney biopsies; may fail when applied to patients already receiving immunosuppressive therapy or with late‑stage disease, when sample processing protocols differ (no cryopreservation or different batch correction), when sample sizes are much smaller than studied (substantially fewer than 10 cases), or when protein‑level/functional validation is required (transcript changes may not reflect protein/activity).
