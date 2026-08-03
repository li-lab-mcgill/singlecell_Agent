---
paper_id: flash_mm_2026
title: "FLASH-MM: fast and scalable single-cell differential expression analysis using linear mixed-effects models."
doi: "10.1038/s41467-026-69063-2"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12982622/"
source_ids: {doc_id: "pmc:12982622", pmid: "41644528", pmcid: "12982622", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_differential_expression"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Identify what statistical unit of inference credible single-cell disease-control studies use for differential molecular state claims, and what failure modes arise if cells are treated as independent replicates."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
FLASH-MM is a fast and scalable linear mixed-effects model estimation algorithm for single-cell RNA-seq differential expression analysis. It keeps cell-level observations while modeling subject-level random effects, individual variation, and covariates, reducing the computational and memory burden of conventional LMM fitting for large scRNA-seq datasets.

## Hypothesis framed
Linear mixed-effects models for scRNA-seq differential expression can be reformulated to use compact summary statistics, enabling subject-aware differential expression testing with controlled false positive rates, high power, and substantially lower computational cost than conventional LMM implementations.

## Questions answered
- Can a linear mixed-effects model for scRNA-seq differential expression be fit at large scale while accounting for subject-level correlation and covariates?
- Does FLASH-MM control false positive rates and maintain statistical power in simulated scRNA-seq differential expression analyses?
- Can FLASH-MM accelerate differential expression testing in real tuberculosis immune-cell and kidney single-cell datasets while preserving subject-level random effects?

## Key findings
FLASH-MM produced accurate linear mixed-effects model parameter estimates for large-scale scRNA-seq differential expression analysis. In simulations based on negative binomial scRNA-seq data, it effectively controlled false positive rates and maintained high statistical power. In tuberculosis immune-cell and kidney single-cell datasets, it accelerated differential expression analysis while allowing covariates and subject-level random effects to be included.

## Methods used
The paper reformulated linear mixed-effects model estimation to operate on compact summary statistics instead of full cell-level matrices. It shifted matrix operations from cell-by-cell matrices to lower-dimensional matrices defined by the numbers of fixed and random effects, supported maximum likelihood and restricted maximum likelihood estimation, and used gradient descent. Evaluation used simulations based on negative binomial scRNA-seq data and real-data applications to tuberculosis immune-cell and kidney single-cell datasets.

## Method and dataset
Method: FLASH-MM linear mixed-effects model estimation for scRNA-seq differential expression. Data type: single-cell RNA-seq gene expression. Datasets: negative binomial simulation datasets, tuberculosis immune-cell single-cell data, and kidney single-cell data; exact cell, donor, and gene counts are not reported in the provided summary. Experimental design: multi-subject scRNA-seq differential expression with fixed effects for conditions or covariates and random effects for subject-level correlation. Assumptions: expression values after transformation or modeling are suitable for an LMM; fixed and random effects are correctly specified; the numbers of fixed and random effects are small relative to the number of cells.

## Limitations
The provided summary does not report quantitative runtime, memory, or accuracy benchmarks. FLASH-MM relies on linear mixed-effects modeling, so validity depends on transformed or summarized scRNA-seq expression satisfying LMM assumptions. Simulations used negative binomial-generated data and method-of-moments dispersion estimates, which may not capture complex zero inflation, technical artifacts, nonlinear effects, or all properties of real scRNA-seq data. The method requires correct fixed-effect and random-effect specification, and performance in complex multi-batch, nested, or higher-order random-effect designs was not established in the summary.

## Evidence pattern
Statistical unit: cells are modeled as observations with subject-level random effects to account for non-independence among cells from the same donor or subject. Comparison design: simulations and real-data applications compared FLASH-MM behavior against conventional LMM fitting concepts, with emphasis on computational scaling and inference quality. Metrics: false positive rate control, statistical power, parameter estimation accuracy, computational complexity, and memory usage. Covariates: fixed effects can include condition, batch, clinical, or other covariates; random effects model subject-level variation. Validation: negative binomial scRNA-seq simulations plus tuberculosis immune-cell and kidney single-cell applications. Boundary conditions: evaluated for scRNA-seq differential expression designs where subject-level correlation and covariates matter.

## Extends or contradicts
This paper extends donor-aware single-cell differential expression analysis by making linear mixed-effects models computationally scalable enough to retain cell-level observations rather than aggregating to pseudobulk profiles. It does not directly contradict a named prior paper in the provided summary.

## Boundary conditions
Works when: Works when the study is multi-subject scRNA-seq, cells from the same subject are correlated, donor or subject identity can be represented as a random effect, biological condition and covariates can be represented as fixed effects, and the numbers of fixed and random effects are much smaller than the number of cells. It is intended for large gene-by-cell datasets where conventional LMM fitting is too slow or memory-intensive.
Fails when: May fail or give unreliable inference when the LMM assumptions are inappropriate for the transformed expression data, when zero inflation or technical artifacts dominate the signal, when fixed or random effects are misspecified, when the design requires complex nested or crossed random-effect structures not evaluated in the summary, or when donor-level replication is insufficient to estimate subject-level variation credibly.
