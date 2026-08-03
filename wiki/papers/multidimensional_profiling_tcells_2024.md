---
paper_id: multidimensional_profiling_tcells_2024
title: "Multidimensional profiling of human T cells reveals high CD38 expression, marking recent thymic emigrants and age-related naive T cell remodeling."
doi: "10.1016/j.immuni.2024.08.019"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC13138122/"
source_ids: {doc_id: "pmc:13138122", pmid: "39321807", pmcid: "13138122", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "multi_cell_type_annotation", "rna_cell_type_annotation"]
retrieval_goals: ["broad_background"]
retrieval_intents: ["Retrieve canonical PBMC scRNA marker references defining major immune cell markers and T/B/monocyte/DC/NK subsets"]
extends: ["integrated_pbmc_atlas_aging_2024"]
added: 2026-05-15
session: unknown
---

## Summary
Using large-scale single-cell RNA/ATAC multiomic data and high-dimensional spectral cytometry across cohorts, the study identifies a SOX4+ IKZF2+ TOX+ naive T cell population corresponding to recent thymic emigrants (RTEs) and validates high surface CD38 (CD38hi/CD38++) as a universal marker for CD4+ and CD8+ RTEs. Cross-sectional profiling of ~158 individuals shows an age-associated decline in CD38++ RTEs and a concurrent increase of CXCR3hi naive-like cells, defining two common axes of naive T cell aging with implications for thymic health readouts and vaccine responsiveness.

## Hypothesis framed
Human recent thymic emigrants (RTEs) are a transcriptionally and epigenetically distinct naive T cell subset that can be robustly identified across individuals by high surface CD38 expression (CD38hi), and the abundance of these CD38hi RTEs declines with age while a CXCR3hi naive-like population increases.

## Questions answered
- Can human recent thymic emigrants (RTEs) be defined by a reproducible transcriptional and epigenetic signature?
- Does high surface CD38 expression (CD38hi/CD38++) mark both CD4+ and CD8+ RTEs in peripheral blood?
- How do naive CD4+ and CD8+ T cell compartments remodel with human aging (compositional axes and cytokine-potential shifts)?

## Key findings
1) A SOX4+ IKZF2+ TOX+ transcriptional and epigenetic naive T cell subset corresponds to human RTEs. 2) High surface CD38 expression (CD38hi / CD38++) reliably marks RTEs in both CD4+ and CD8+ compartments and was validated by flow/spectral cytometry. 3) Analysis of ABF300 PBMC aging cohort (naive CD8 n=102,842; naive CD4 n=457,034 cells) plus cross-sectional cohorts (total ~158 individuals) showed an age-dependent decline of CD38++ RTEs and a concurrent increase of a CXCR3hi naive-like population, defining two conserved axes of naive T cell aging. 4) RTEs have distinct epigenetic states and altered cytokine-production potential vs. mature naive cells. 5) Findings were reproduced across independent public datasets and validated in neonatal and thymectomized samples.

## Methods used
Single-cell RNA-seq, single-cell ATAC-seq, multiome integration, clustering and marker discovery, peak/transcriptional regulatory analysis, high-dimensional spectral/flow cytometry validation, cross-sectional cohort statistical analyses, comparison to public datasets and neonatal/thymectomy samples.

## Method and dataset
Multiomic single-cell RNA and ATAC profiling from the ABF300 PBMC aging cohort (naive CD8 n=102,842; naive CD4 n=457,034 cells) with multiomic integration to link chromatin and transcriptomic signatures to protein; high-dimensional spectral cytometry and flow cytometry on cross-sectional cohorts totaling ~158 individuals plus independent public datasets and neonatal/thymectomized samples. Methods assume measured surface CD38 accurately reflects the RTE transcriptional/epigenetic signature in peripheral blood and that cross-sectional age differences proxy age-related remodeling.

## Limitations
Primarily cross-sectional aging analyses limit longitudinal inference; some validation cohorts were demographically restricted (e.g., Caucasian, non-obese), limiting generalizability; CD38 expression is activation-sensitive and may be modulated in inflammatory or clinical contexts, which could confound specificity as a thymic-output marker; functional impacts on vaccine or infection responses were not prospectively demonstrated.

## Evidence pattern
entity_definition, validation, statistical_unit, comparison_design, boundary_conditions, analysis_used

## Extends or contradicts
Extends integrated_pbmc_atlas_aging_2024 by providing a distinct RTE transcriptional/epigenetic signature and a universal surface marker (CD38hi) linking thymic output to peripheral naive T cell composition.

## Boundary conditions
Works when: Applied to peripheral blood PBMC single-cell multiome (RNA+ATAC) datasets with large naive T cell counts (examples: naive CD8 >100k, naive CD4 >400k aggregated) and cross-sectional cohorts of hundreds of individuals; validated by spectral/flow cytometry on unstimulated peripheral blood and in neonatal and thymectomized samples; best when samples are profiled ex vivo (not recently activated) and when protein cytometry panels include CD38 and CXCR3.
Fails when: Marker specificity is compromised in settings with recent T cell activation, strong inflammation, or therapies that upregulate CD38; not validated across diverse ancestries, obese populations, or many disease states; small sample sizes or datasets lacking protein/surface measurements (cytometry) reduce ability to map transcriptional RTE signature to surface CD38; longitudinal dynamics cannot be directly inferred from cross-sectional data.
