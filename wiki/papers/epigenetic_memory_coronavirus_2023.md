---
paper_id: epigenetic_memory_coronavirus_2023
title: "Epigenetic memory of coronavirus infection in innate immune cells and their progenitors."
doi: "10.1016/j.cell.2023.07.019"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC10638861/"
source_ids: {doc_id: "pmc:10638861", pmid: "37597510", pmcid: "10638861", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_differential_accessibility", "atac_motif_analysis", "multiomic_integration"]
retrieval_goals: ["prior_findings"]
retrieval_intents: ["Canonical PBMC cell type and subtype marker genes expected in human PBMC scRNA-seq and corresponding ATAC motif/peak signatures."]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
Using multimodal single-nucleus RNA+ATAC (multiome), bulk/single-nucleus ATAC, flow cytometry, and plasma proteomics in a cohort of 168 participants, the study shows that severe COVID-19 induces durable epigenetic and transcriptional reprogramming of circulating HSPC and their myeloid progeny that persists months to one year and is associated with increased myelopoiesis and IL-6–linked TF activity. Experimental mouse coronavirus infection and IL-6 perturbation support a role for early IL-6 activity in establishing these long-lived phenotypes.

## Hypothesis framed
Severe SARS-CoV-2 infection induces durable epigenetic and transcriptional memory in circulating human HSPC that is transmitted to myeloid progeny and is driven in part by early IL-6 activity.

## Questions answered
- Does severe COVID-19 induce durable epigenetic reprogramming in circulating human HSPC lasting months to one year?
- Are HSPC epigenomic alterations transmitted to differentiated monocytes and do these progeny show altered inflammatory responsiveness?
- Does early IL-6 activity contribute to the establishment of durable HSPC and monocyte phenotypes following coronavirus infection?

## Key findings
In a cohort of 168 participants (groups: Healthy, nonCoV critical illness, Early convalescent 2–4 months, Late convalescent 4–12 months), single-nucleus multiome and ATAC profiling (ATAC subset n≈57) identified durable chromatin accessibility changes and TF motif activity in circulating HSPC after severe COVID-19 that persisted up to 1 year. Reprogrammed HSPC displayed increased myelopoiesis and elevated granulocyte-monocyte progenitor (GMP) frequencies, epigenetic poising of inflammatory genes, and IL-6–associated TF signatures; these chromatin and TF signatures were transmitted to differentiated monocytes which exhibited hyper-responsiveness to stimulation. Principal component analysis separated post-COVID (Early+Late) signatures from non-COVID critical illness. Mouse coronavirus infection and IL-6 perturbation experiments supported a contributing role for early IL-6 activity.

## Methods used
Peripheral blood enrichment of circulating HSPC; single-nucleus multiome (paired snRNA+snATAC) profiling; bulk and single-nucleus ATAC-seq; flow cytometry immunophenotyping; plasma protein multiplexing; differential accessibility (DAR) analysis; TF motif activity inference; PCA; comparative cohort design (Healthy, nonCoV, Early, Late); mouse coronavirus infection model and IL-6 perturbation experiments; data deposition (GEO GSE196990).

## Method and dataset
Paired snRNA+snATAC multiome and ATAC-seq on circulating HSPC and PBMC from a cohort of 168 human participants enrolled Mar 2020–Mar 2021 (pre-vaccine, early variants); convalescent sampling binned as 2–4 months (Early) and 4–12 months (Late) post-infection; ATAC profiling performed on a subset (~n=57). Analyses assume circulating peripheral-blood–enriched HSPC reasonably represent bone marrow HSPC epigenomic states and use TF motif/activity inference from chromatin accessibility to link regulatory programs to gene expression.

## Limitations
Used circulating peripheral-blood–enriched HSPC as a proxy for bone marrow HSPC (no direct marrow sampling); cohort limited to first pandemic wave (unvaccinated, early variants) which limits generalizability to vaccinated individuals or later variants; observational design with smaller subsets for multi-omic assays (e.g., ~57 for ATAC) limits causal inference despite supportive mouse experiments; clinical heterogeneity and treatments are potential confounders; findings focused on severe COVID-19 rather than mild disease.

## Evidence pattern
entity_definition,comparison_design,statistical_unit,effect_metric,controls_covariates,validation,boundary_conditions

## Extends or contradicts
Extends prior mouse and controlled human vaccine studies demonstrating that HSPC can store inflammatory memory by demonstrating durable HSPC epigenetic reprogramming after acute human coronavirus infection and transmission of these signatures to myeloid progeny; does not contradict those prior findings.

## Boundary conditions
Works when: Works when: peripheral-blood circulating HSPC are enriched from adult human donors infected with early SARS-CoV-2 variants (pre-vaccine), cohort-size similar to n≈168 with multi-omic ATAC subset ~50–60, samples collected at 2–12 months post severe infection, paired snRNA+snATAC (multiome) and plasma proteomics (including IL-6) are available, and analyses include DAR and TF motif activity inference.
Fails when: Fails when: applied to vaccinated individuals or infections by later SARS-CoV-2 variants without revalidation; in cohorts dominated by mild/asymptomatic cases rather than severe COVID-19; when only marrow HSPC are available without peripheral circulating HSPC enrichment (assumption violated); when dataset lacks sufficient cells for ATAC (e.g., ATAC n << 50) or lacks plasma IL-6 measurements; or when experimental conditions differ (no matched multiome data or differing timepoints outside 2–12 months).
