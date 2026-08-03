---
paper_id: glimes_scde_2025
title: "Exploring and mitigating shortcomings in single-cell differential expression analysis with a new statistical paradigm."
doi: "10.1186/s13059-025-03525-6"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC11912664/"
source_ids: {doc_id: "pmc:11912664", pmid: "40098192", pmcid: "11912664", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_differential_expression", "rna_batch_correction"]
retrieval_goals: ["broad_background"]
retrieval_intents: ["What statistical guidance establishes that donors/samples, not cells, are the valid replication unit for inference (to avoid pseudoreplication) in single-cell RNA/ATAC studies?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
Introduces GLIMES, a generalized Poisson/Binomial mixed-effects framework that models raw UMI counts and zero proportions with donor/batch random effects to address excessive zeros, normalization artifacts, donor effects, and cumulative biases in single-cell DE analysis. Benchmarked against six widely used methods on simulations and three case studies (including fallopian tube data), GLIMES preserved absolute expression signals, improved sensitivity, reduced false discoveries, and produced DE lists more consistent with biological expectations.

## Hypothesis framed
Modeling raw UMI counts together with observed zero proportions in a generalized Poisson/Binomial mixed-effects model that includes donor/batch random effects will (1) reduce false discoveries caused by normalization and pseudoreplication, (2) preserve absolute RNA expression signals, and (3) improve sensitivity and biological interpretability of single-cell differential expression results relative to existing methods.

## Questions answered
- Does GLIMES (generalized Poisson/Binomial mixed-effects on raw UMI counts and zero proportions) outperform pseudo-bulk (DESeq2/edgeR), MAST, Seurat Wilcoxon, and Muscat mixed models across simulated and real single-cell RNA-seq scenarios with donor/batch structure?
- Does modeling donor/batch as random effects and using absolute UMI counts reduce false discoveries and prevent shrinkage of absolute expression differences introduced by common normalization/integration methods?

## Key findings
GLIMES outperformed six comparator methods across simulations and three real case studies (including fallopian tube comparisons) by (a) preserving absolute RNA expression signals and avoiding the shrinkage seen with VST and aggressive integration, (b) improving sensitivity to detect DE genes while reducing false discoveries associated with normalization and unmodeled donor effects, and (c) producing DE lists and GO enrichments that aligned better with biological expectations. The paper also demonstrated that some standard pipelines (e.g., pseudo-bulk DESeq2 with default QC) can dramatically reduce the tested gene universe and thus affect results.

## Methods used
Developed GLIMES: generalized Poisson mixed-effects model for UMI counts plus Binomial mixed model for observed zero proportions; included donor/batch random effects and within-sample variation. Benchmarks: simulations across experimental scenarios, three real case studies (fallopian tube and others), comparisons to pseudo-bulk DESeq2/edgeR, MAST zlm, Seurat Wilcoxon (v4/v5) workflows, Muscat mixed models; diagnostic plots, t-score comparisons, and Gene Ontology enrichment analyses.

## Method and dataset
Method: GLIMES (generalized Poisson for UMI counts + Binomial for zero proportions) implemented as mixed-effects models including donor/batch random effects and within-sample variation. Data: UMI-based single-cell RNA-seq datasets (three case studies including fallopian tube data) and simulation datasets spanning homogeneous/heterogeneous groups, variable/similar library sizes, and comparisons across cell types, tissue regions, and cell states. Approximate sample sizes not reported in summary. Key assumptions: UMI counts are well modeled by generalized Poisson, zero proportions informative and modeled by Binomial, random effects correctly specified, and adequate donor/sample replication.

## Limitations
Evaluations limited to the included simulations and three case studies; may not generalize to all tissues, protocols, or non-UMI platforms. GLIMES depends on model assumptions (generalized Poisson/Binomial, correctly specified random effects) and adequate donor/sample replication; performance may degrade with model misspecification, extreme sparsity, insufficient donors, or non-UMI chemistries. Implementation complexity and computational resource requirements may be substantial and require further practical benchmarking.

## Evidence pattern
comparison_design; statistical_unit (explicit modeling of donor/sample as random effects); controls_covariates (batch/donor covariates included as random effects); validation (simulations + three real case studies); metrics (sensitivity, false discovery/bias reduction, t-score comparisons, GO enrichment for biological plausibility); analysis used (benchmarks vs six established methods, diagnostic plots).

## Extends or contradicts
Extends critiques of workflows that treat cells as independent replicates and that emphasize relative RNA abundance after normalization; contradicts practices that ignore donor/batch structure (cell-as-sample pseudoreplication) by providing empirical evidence that donor/sample-level modeling reduces bias and false discoveries.

## Boundary conditions
Works when: Works when input data are UMI-based single-cell RNA-seq with measurable zero proportions; when there is adequate donor/sample replication to estimate random effects; when generalized Poisson/Binomial assumptions are reasonable for counts and zeros; applicable across designs comparing cell types, tissue regions, or cell states and in presence of batch/donor structure.
Fails when: Fails or is unreliable for non-UMI platforms (e.g., full-length protocols without UMIs), when donor/sample replication is too small to estimate random effects (very few donors), under extreme sparsity where model assumptions break down, with severe model misspecification, or when computational resources are insufficient to fit mixed-effects models.
