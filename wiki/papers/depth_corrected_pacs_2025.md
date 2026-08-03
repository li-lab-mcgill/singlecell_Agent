---
paper_id: depth_corrected_pacs_2025
title: "Depth-corrected multi-factor dissection of chromatin accessibility for scATAC-seq data with PACS."
doi: "10.1038/s41467-024-55580-5"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC11701134/"
source_ids: {doc_id: "pmc:11701134", pmid: "39757254", pmcid: "11701134", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_differential_accessibility", "atac_cell_type_annotation", "atac_batch_correction"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Establish what null models, covariate controls, and multiple-testing frameworks are required for statistically valid single-nucleus ATAC differential accessibility, TF/motif enrichment, and peak-to-gene regulatory association inference."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This paper introduces PACS, a depth-corrected zero-adjusted statistical framework for scATAC-seq that models chromatin accessibility at candidate cis-regulatory elements under multifactor experimental designs. PACS accounts for sparse and incomplete scATAC-seq observations and cell-level capture probability, enabling differential accessibility testing, supervised cell type annotation, batch correction, and spatial or temporal effect modeling.

## Hypothesis framed
A zero-adjusted latent accessibility model that jointly accounts for group-level accessibility effects and cell-level capture probability can provide better-calibrated and more powerful scATAC-seq differential accessibility inference than existing approaches under complex multifactor designs.

## Questions answered
- Does PACS control false positive rates for scATAC-seq differential accessibility analysis while accounting for cell-specific capture depth?
- Does PACS improve statistical power for differential accessibility testing compared with existing scATAC-seq tools?
- Can PACS support compound hypothesis testing, batch effect correction, and supervised cell type annotation in multifactor scATAC-seq datasets?

## Key findings
PACS controlled false positive rates in differential accessibility analysis and achieved 17% to 122% higher average statistical power than existing tools. It improved supervised cell type annotation relative to a Naive Bayes approach that does not model cell-specific capture differences. Across multiple tissue scATAC-seq datasets, PACS supported compound hypothesis testing, batch effect correction, atlas-level annotation transfer, and spatiotemporal accessibility modeling.

## Methods used
PACS uses a zero-adjusted cumulative-logit-style probability model for integer-valued paired insertion count measurements at candidate cis-regulatory elements. It represents known covariates with a cell-by-factor design matrix, models observed insertion counts as measurements of latent accessibility states, and jointly estimates group-level accessibility effects and cell-level capture probability. The paper evaluated PACS using differential accessibility analysis, supervised cell type annotation, batch correction, compound hypothesis testing, and spatial or temporal modeling across scATAC-seq datasets from multiple tissues.

## Method and dataset
The method was applied to scATAC-seq data measuring paired insertion counts at candidate cis-regulatory elements or peaks. Dataset sizes are not specified in the provided summary. The experimental designs included multiple possible accessibility-modulating factors such as genotype, cell type, tissue of origin, sample location, batch, spatial location, and developmental time. PACS assumes that observed sparse insertion counts arise from latent chromatin accessibility states and cell-specific capture probabilities, and that relevant predictors are encoded in a specified design matrix.

## Limitations
The provided summary does not report extensive empirical limitations. PACS depends on accurate specification of design factors and peak or candidate regulatory element definitions. Its validity may be affected by unmodeled confounders, very low-quality or extremely sparse scATAC-seq data, violations of the latent accessibility or missingness assumptions, and the computational cost of fitting multifactor models at atlas scale. The summary does not specify motif or TF enrichment null models, peak-to-gene linkage null models, donor-level mixed effects, or the multiple-testing procedure beyond false-positive-rate control.

## Evidence pattern
The paper supports its claims through method definition, comparison design against existing differential accessibility tools, false-positive-rate and statistical-power evaluation, supervised annotation comparison against a Naive Bayes baseline, covariate-controlled multifactor modeling using a cell-by-factor design matrix, and validation across multiple scATAC-seq tissue datasets.

## Extends or contradicts
This work extends existing scATAC-seq differential accessibility and annotation approaches by explicitly modeling sparse paired insertion counts, latent accessibility states, multifactor covariates, and cell-level capture probability. No specific prior wiki paper is identified in the provided summary as directly extended or contradicted.

## Boundary conditions
Works when: Works when scATAC-seq data have defined candidate cis-regulatory elements or peaks, integer paired insertion count measurements, known cell-level covariates encoded in a design matrix, and experimental questions involving genotype, cell type, tissue, spatial location, developmental time, batch, or other specified accessibility-modulating factors.
Fails when: May fail or lose validity when important confounders are absent from the design matrix, peak definitions are poor, datasets are extremely sparse or low quality, capture probability is not adequately described by the model, latent accessibility assumptions are violated, or the analysis requires motif enrichment, TF enrichment, peak-to-gene linkage, donor-level pseudobulk replication, or mixed-effects donor controls not described in the provided summary.
