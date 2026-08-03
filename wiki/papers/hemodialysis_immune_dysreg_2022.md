---
paper_id: hemodialysis_immune_dysreg_2022
title: "Single-Cell RNA and ATAC Sequencing Reveal Hemodialysis-Related Immune Dysregulation of Circulating Immune Cell Subpopulations."
doi: "10.3389/fimmu.2022.878226"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9205630/"
source_ids: {doc_id: "pmc:9205630", pmid: "35720370", pmcid: "9205630", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "rna_differential_expression", "atac_motif_analysis"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["Retrieve GLUE paper and summarize PBMC biological validation patterns for RNA+ATAC integration."]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
This study integrates scRNA-seq and scATAC-seq on pooled PBMCs from 10 maintenance hemodialysis (HD) patients and 10 matched healthy controls to characterize HD-associated transcriptional and chromatin accessibility changes. It identifies suppressed TCR gene expression in CD4+ T cells, downregulated MHC-II genes in monocytes, reduced AP-1 motif accessibility with lower AP-1 TF expression, and validates selected DE genes by qRT-PCR on magnetically separated CD4+ T cells and monocytes.

## Hypothesis framed
Long-term maintenance hemodialysis alters transcriptional programs and chromatin accessibility of circulating PBMC subpopulations, producing measurable immune dysregulation in T cell and monocyte compartments.

## Questions answered
- Does long-term maintenance hemodialysis alter transcriptional programs and chromatin accessibility across circulating PBMC subpopulations?
- Which PBMC subsets show suppression of TCR-related genes and antigen presentation (MHC-II) genes in HD patients?
- Is reduced chromatin accessibility at AP-1 family loci associated with decreased AP-1 TF expression in HD PBMCs?

## Key findings
Using pooled single-cell data (10 HD vs 10 controls) the study identified 16 scRNA and 15 scATAC PBMC subpopulations. Bulk RNA-seq found ~3,355 DE genes in HD PBMCs with downregulation of B- and T-cell receptor signaling and antigen processing/presentation. At single-cell resolution, TCR genes (examples: TRAV4, CD45, CD3G, CD3D, CD3E) were suppressed in CD4+ T cell subsets (including naive and effector memory cells); MHC-II genes (HLA-DRB1, HLA-DQA1, HLA-DQA2, HLA-DPB1) were downregulated in monocytes. Downstream TCR signaling pathways (PI3K-Akt-mTOR, MAPK, TNF, NF-κB) were inhibited in CD4+ T cell subpopulations. Predicted intercellular signaling between CD4+ T cells and monocytes was altered (notably TGF-TGFBR, HVEM-BTLA, IL16-CD4). scATAC-seq showed reduced chromatin accessibility at AP-1 family loci with decreased AP-1 TF expression (JUN, JUND, FOS, FOSB). Selected DE genes were validated by magnetic-bead separation of CD4+ T cells and monocytes followed by qRT-PCR. Samples for single-cell libraries were pooled by group prior to 10x library generation.

## Methods used
Peripheral blood mononuclear cell isolation; pooling of cells by group (HD vs control) prior to library prep; 10x Genomics single-cell RNA-seq and single-cell ATAC-seq; bulk RNA-seq on a subset (3 HD, 3 controls); clustering to identify cell subpopulations; differential expression analysis; GSEA/KEGG pathway analysis; ImmPort immune gene interrogation; cell–cell communication inference; chromatin accessibility and TF motif activity analysis; magnetic-bead separation of CD4+ T cells and monocytes and qRT-PCR validation.

## Method and dataset
Applied scRNA-seq and scATAC-seq (10x Genomics) to PBMCs pooled within group from 10 maintenance hemodialysis patients and 10 matched healthy controls (single-cell libraries pooled by group). Bulk RNA-seq performed on PBMCs from 3 HD and 3 controls. Analysis identified 16 scRNA and 15 scATAC clusters and linked differential gene expression to pathway perturbation and TF motif accessibility. Assumes that pooled-group libraries represent group-level differences (statistical unit effectively: pooled group), and that 10x assays capture representative nuclei/cells from each pooled sample.

## Limitations
Relatively small sample size and single-center recruitment limit generalizability; single-cell samples were pooled by group before library preparation, preventing per-donor single-cell comparisons and introducing potential donor-bias; cross-sectional design prevents causal inference or temporal dynamics; functional validation limited to qRT-PCR on separated subsets (no protein-level assays, perturbations, or external replication cohort); possible unmeasured confounders (comorbidities, dialysis parameters, medications) may affect results.

## Evidence pattern
comparison_design (HD vs matched healthy controls), validation (qRT-PCR on magnetically separated CD4+ T cells and monocytes), statistical_unit: pooled-group single-cell libraries, controls_covariates: matched controls with stated exclusions, boundary_conditions: single-center, cross-sectional, pooled samples; analysis_used: scRNA-seq + scATAC-seq integration, bulk RNA-seq, DE analysis, GSEA/KEGG, ImmPort gene interrogation, cell-cell communication inference, TF motif accessibility analysis.

## Extends or contradicts
Extends prior reports of impaired T-lymphocyte responses and antigen-presenting cell preactivation in maintenance hemodialysis by providing single-cell transcriptional and chromatin accessibility evidence linking suppressed TCR gene expression in CD4+ T cells and reduced MHC-II expression/accessibility in monocytes; does not report direct contradictions to prior findings.

## Boundary conditions
Works when: Works for detecting group-level transcriptional and chromatin differences between maintenance hemodialysis patients and matched controls when PBMCs are pooled by group and profiled with 10x Genomics scRNA-seq and scATAC-seq; sample sizes on the order of ~10 donors per group with validation by qRT-PCR on sorted cell subsets.
Fails when: Fails when per-donor single-cell resolution or donor-level variability is required (samples were pooled), when longitudinal or causal inference is needed (cross-sectional design), when different dialysis modalities or unmeasured confounders vary systematically across groups, or when protein-level or functional perturbation validation is required (only qRT-PCR validation performed).
