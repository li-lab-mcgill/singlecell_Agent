---
paper_id: psychological_stress_social_support_2025
title: "Psychological stress and social support are associated with opposing single-cell pro-inflammatory gene regulatory mechanisms in adults."
doi: "10.1101/2025.10.14.682318"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12632774/"
source_ids: {doc_id: "pmc:12632774", pmid: "41278935", pmcid: "12632774", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "atac_motif_analysis", "multi_grn_inference"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["What biological validation and expected structures does the Seurat v4 WNN paper establish for paired scRNA+scATAC PBMC datasets?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
Analyzed paired scRNA-seq (558,291 cells) and scATAC-seq (400,535 cells) from PBMCs of 165 self-reported African American adults to link psychological stress and social support to single-cell gene regulatory programs. Found opposing pro-inflammatory/interferon regulatory signatures across CD4+ T cells and monocytes, supported by circulating cytokine correlations and LPS ex vivo stimulation validation.

## Hypothesis framed
Psychological stress and social support modulate single-cell gene regulatory programs in peripheral blood immune cells, producing opposing effects on pro-inflammatory/interferon signaling.

## Questions answered
- Do self-reported psychological stress and social support associate with differential gene expression and chromatin-based TF motif activity in PBMC cell types?
- Are interferon-signaling genes and IRF/STAT motif activities increased with high psychological stress and decreased with high social support?
- Do scATAC-derived motif activity changes overlap with differentially expressed genes and correspond to elevated circulating IFN-γ, TNF-α, IL-6 and to LPS stimulation responses?

## Key findings
Psychological stress was associated with 1,956 differentially expressed genes (10% FDR), predominately in monocytes and CD4+ T cells. Social support was associated with 1,296 DEGs, notably in CD4+ and CD8+ T cells and monocytes. Genome-wide TF motif analysis identified 70 motifs linked to stress and 116 motifs linked to social support; 87 motifs were enriched near DEGs and ~90% of motif changes overlapped DEGs. High psychological stress corresponded to increased IRF and STAT motif activity and expression of interferon-response genes; social support showed the opposite pattern. Expression signatures associated with stress mirrored higher circulating IFN-γ, TNF-α, and IL-6. Ex vivo LPS stimulation confirmed activation of implicated pathways.

## Methods used
Paired single-cell RNA-seq (558,291 cells) and single-cell ATAC-seq (400,535 cells) on PBMCs; cell clustering and annotation into major immune types (CD4+/CD8+ T cells, NK, monocytes, B cells); differential expression analysis at 10% FDR; genome-wide TF motif activity inference from scATAC-seq; enrichment of motifs near DEGs (peak-to-gene proximity linkage); circulating cytokine measurement (IFN-γ, TNF-α, IL-6); ex vivo LPS immune challenge for pathway validation.

## Method and dataset
Integrated scRNA-seq and scATAC-seq (paired) from 165 human donors (self-reported African American, age 50–89) collected 2017–2020; dataset sizes: ~558k scRNA cells, ~400k scATAC cells; analyses assumed reliable cell-type annotation of major PBMC populations, sufficient per-cell-type cell counts for differential testing, and that motif activity inferred from chromatin accessibility reflects TF regulatory activity; experimental design was cross-sectional with separate modeling of psychological stress and social support and biological validation via circulating cytokines and LPS stimulation.

## Limitations
Cross-sectional observational design prevents causal inference; psychosocial exposures were self-reported; cohort restricted to middle-aged/older self-reported African American adults from one urban area limiting generalizability; analyses used a 10% FDR which may include false positives; potential residual confounding and batch effects; single timepoint peripheral blood sampling does not capture temporal or tissue-specific dynamics; no explicit description or benchmarking of integration algorithm details (e.g., Seurat WNN parameters) in the summary.

## Evidence pattern
entity_definition (PBMC cell types: CD4+/CD8+ T cells, NK, monocytes, B cells), statistical_unit (single cells nested within 165 donors), comparison_design (modeled psychological stress and social support separately across donors), effect_metric (differential expression at 10% FDR; TF motif activity changes from scATAC; enrichment of motifs near DEGs), covariates (not fully specified in summary), validation (correlation with circulating IFN-γ, TNF-α, IL-6 and ex vivo LPS stimulation), boundary_conditions (cohort demographics, single timepoint), analysis_used (clustering/annotation, DEG testing, genome-wide TF motif inference, motif–DEG proximity enrichment).

## Extends or contradicts
Extends prior multimodal single-cell integration applications (e.g., hao_2021) by applying paired scRNA+scATAC analyses to psychosocial exposures in a sizeable donor cohort and adding biological validation via cytokine correlations and LPS stimulation.

## Boundary conditions
Works when: Paired scRNA+scATAC PBMC data from human donors with large aggregate cell counts (here ~558k RNA cells and ~400k ATAC cells) and adequate per-cell-type representation (notably CD4+ T cells and monocytes); donor-level sample size in the dozens-to-hundreds (here n=165) enabling population-level association testing; availability of complementary validation data (circulating cytokines and ex vivo immune challenge) to support regulatory inferences.
Fails when: Unpaired modalities or small datasets (e.g., <50 donors or low total cell counts) where per-cell-type counts are insufficient; different tissues than peripheral blood; cohorts with different demographics (younger, non–African American, non-urban) without replication; absence of orthogonal validation (no cytokine measurements or immune stimulation); when causal inference is required (cross-sectional design cannot establish causality).
