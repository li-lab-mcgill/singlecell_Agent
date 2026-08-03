---
paper_id: pacs_allows_comprehensive_dissection
title: "PACS allows comprehensive dissection of multiple factors governing chromatin accessibility from snATAC-seq data."
doi: "10.1101/2023.07.30.551108"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC10418058/"
source_ids: {doc_id: "pmc:10418058", pmid: "37577623", pmcid: "10418058", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_differential_accessibility", "atac_cell_type_annotation", "atac_batch_correction"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Establish what null models, covariate controls, and multiple-testing frameworks are required for statistically valid single-nucleus ATAC differential accessibility, TF/motif enrichment, and peak-to-gene regulatory association inference."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This paper presents PACS, a zero-adjusted latent-variable statistical framework for snATAC-seq that models observed insertion counts as incomplete measurements of underlying chromatin accessibility while separating group-level accessibility from cell-level read recovery. PACS supports differential accessibility testing, supervised cell-type annotation, compound covariate hypothesis testing, batch-effect correction, and spatiotemporal modeling in sparse snATAC-seq datasets with complex experimental designs.

## Hypothesis framed
A zero-adjusted model that explicitly accounts for incomplete chromatin accessibility observations and cell-specific read capture can control false positive rates and improve power for snATAC-seq differential accessibility and multi-factor hypothesis testing compared with existing approaches.

## Questions answered
- Does PACS control false positive rates and improve statistical power for snATAC-seq differential accessibility testing compared with existing tools?
- Can explicit modeling of cell-specific read capture improve supervised snATAC-seq cell-type annotation compared with a Naive Bayes model that ignores capture variation?
- Can a design-matrix-based PACS model test compound effects of covariates such as cell type, developmental time, spatial location, stimulation state, and batch in snATAC-seq data?

## Key findings
PACS controlled false positive rates in differential accessibility testing and achieved reported average power gains of 17% to 122% over existing tools. Modeling cell-specific read recovery improved supervised cell-type annotation compared with a Naive Bayes approach that did not account for capture variation. Across mouse kidney, human cell line, developing human brain, marmoset brain, and human PBMC stimulation time-series snATAC-seq datasets, PACS supported multi-factor tests involving cell type, developmental time, spatial location, stimulation, and batch and identified regulatory patterns not readily detected by existing approaches.

## Methods used
PACS uses paired insertion count matrices, a zero-adjusted latent accessibility model, a missing-corrected cumulative logistic regression model, regularization, and a covariate design matrix for hypothesis testing. The authors evaluated PACS using differential accessibility benchmarks, false-positive-rate and power comparisons against existing tools, supervised cell-type annotation benchmarks, compound hypothesis tests, batch-effect correction analyses, and spatiotemporal modeling applications.

## Method and dataset
The method was applied to snATAC-seq data measured at candidate cis-regulatory elements or peaks, using datasets from mouse kidney, human cell lines, developing human brain, marmoset brain, and human PBMC stimulation time series; exact cell counts and peak counts are not specified in the summary. PACS assumes candidate regulatory elements or peaks are predefined, observed counts are incomplete measurements of latent accessibility, zero observations can reflect either true inaccessibility or capture failure, and relevant biological or technical covariates are encoded correctly in the design matrix.

## Limitations
PACS depends on accurate peak or candidate regulatory element definitions and on the correctness of its latent accessibility and missing-data assumptions. Performance may depend on dataset quality, sequencing depth, sparsity level, and accurate covariate specification in the design matrix. Unmodeled confounders or incomplete experimental metadata can affect interpretation. The summary provides limited detail on computational scalability, runtime, performance in extremely large or highly heterogeneous datasets, donor-level pseudobulk or random-effect modeling, motif enrichment null models, and peak-to-gene linkage inference.

## Evidence pattern
The evidence pattern included candidate cis-regulatory elements as statistical entities, single-nucleus ATAC insertion counts as observations, latent accessibility as the modeled quantity, and covariates such as genotype, cell type, tissue source, spatial location, developmental time, stimulation state, and batch encoded in a design matrix. Claims were supported by comparison designs against existing tools using false-positive-rate control and statistical power for differential accessibility, supervised annotation comparison against Naive Bayes, and validation across multiple public snATAC-seq datasets from different tissues and experimental settings.

## Extends or contradicts
This paper extends existing snATAC-seq differential accessibility and annotation approaches by replacing simple normalization or count-based testing with a zero-adjusted latent-variable model that separates accessibility from cell-specific read capture and supports compound covariate hypothesis tests. It does not directly contradict a specific prior wiki paper in the provided list.

## Boundary conditions
Works when: Works when snATAC-seq data are sparse and have variable read capture across cells, when candidate peaks or cis-regulatory elements have been defined, and when experimental factors such as cell type, batch, genotype, tissue source, spatial location, developmental time, or stimulation state are available as covariates in a design matrix.
Fails when: May fail or give misleading results when peak definitions are inaccurate, sequencing depth or data quality is too low to estimate accessibility distributions reliably, relevant confounders are missing from the design matrix, metadata are incomplete, or the analysis requires explicit donor-level random effects, motif enrichment null models, or peak-to-gene linkage permutation frameworks that are not described in the summary.
