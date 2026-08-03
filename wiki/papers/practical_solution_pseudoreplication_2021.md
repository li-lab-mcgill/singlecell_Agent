---
paper_id: practical_solution_pseudoreplication_2021
title: "A practical solution to pseudoreplication bias in single-cell studies."
doi: "10.1038/s41467-021-21038-1"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC7854630/"
source_ids: {doc_id: "pmc:7854630", pmid: "33531494", pmcid: "7854630", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_differential_expression", "rna_batch_correction", "multi_batch_correction"]
retrieval_goals: ["broad_background"]
retrieval_intents: ["What statistical guidance establishes that donors/samples, not cells, are the valid replication unit for inference (to avoid pseudoreplication) in single-cell RNA/ATAC studies?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
This paper empirically demonstrates that cells from the same individual are correlated (pseudoreplicates) and that treating cells as independent inflates type I error; it compares pseudo-bulk aggregation and mixed models and recommends generalized linear mixed models (GLMMs) with an individual-level random effect for differential expression within cell types, providing accompanying power estimates to guide study design.

## Hypothesis framed
When testing differential expression within a defined cell type, donors/samples (not individual cells) are the valid unit of replication, and using GLMMs with an individual-level random effect properly accounts for within-individual correlation and zero inflation, outperforming naive cell-level tests and pseudo-bulk in terms of error control and power.

## Questions answered
- Do cells from the same individual show higher pairwise correlation than cells from different individuals (demonstrating pseudoreplication)?
- For differential expression within cell types, do pseudo-bulk aggregation approaches or mixed-model (GLMM) approaches better control type I error and power?
- Is treating individual as a batch-correction sufficient to account for within-sample correlation?

## Key findings
Across multiple published scRNA-seq datasets totaling 40,775 cells from 43 individuals, within-individual pairwise Spearman correlations were consistently higher than between-individual correlations, demonstrating hierarchical structure and pseudoreplication risk; methods that treat cells as independent show inflated type I error. Pseudo-bulk aggregation methods were generally conservative and underpowered relative to mixed models. GLMMs with a random effect for individual are recommended to account for zero inflation and within-individual correlation for differential expression within cell types. The authors provide power estimates across experimental conditions to inform required numbers of independent individuals.

## Methods used
Systematic literature review (PubMed search Jan 2019; 251 hits → 76 relevant papers); empirical quantification of intra- and inter-individual Spearman correlations using multiple published single-cell RNA-seq datasets; gene pruning to ≤500 relatively uncorrelated genes (removed gene pairs with Spearman rho > 0.25); computed all within-individual cell-pair correlations and 1,000 draws of one-cell-per-individual to estimate inter-individual correlations; compared aggregation-based pseudo-bulk approaches to mixed models; applied generalized linear mixed models (GLMMs) with an individual-level random effect; generated power simulations/estimates under varying experimental conditions.

## Method and dataset
Applied GLMMs (count-based models accommodating zero inflation) with a random effect for individual to published single-cell RNA-seq datasets spanning diverse cell types, total ~40,775 cells from 43 individuals; experimental design focused on differential expression within specific cell types across treatment groups. Assumptions: cells are nested within independent individuals, counts exhibit zero inflation, and individuals constitute the independent replication units.

## Limitations
Empirical analyses used a limited set of datasets and cell types and may depend on the gene selection/pruning procedure used; literature review only covered studies up to January 2019 (post-2019 methods not evaluated); GLMMs can be computationally intensive and may face convergence issues for very large datasets; adequate numbers of independent individuals are critical for power; limited specific guidance for single-cell ATAC.

## Evidence pattern
entity_definition, statistical_unit, comparison_design, metric (Spearman correlation), validation (empirical across multiple datasets), analysis used (GLMM vs pseudo-bulk), boundary_conditions

## Extends or contradicts
Contradicts practices that treat individual cells as independent replicates or that attempt to correct for the individual by simple batch-effect removal; extends empirical evidence emphasizing donor-level replication and supports mixed-model approaches for within-cell-type differential expression.

## Boundary conditions
Works when: Applies when analyzing scRNA-seq datasets with cells nested within multiple independent donors/samples (demonstrated on datasets totaling 43 individuals and ~40,775 cells), when testing differential expression within defined cell types, when count data exhibit zero inflation and mixed models can be fit, and when gene sets can be pruned as described (≤500 relatively uncorrelated genes) for correlation assessments.
Fails when: Fails or is limited when the study includes very few independent individuals (insufficient for mixed-model estimation and statistical power), when datasets are so large that GLMMs cannot be computed or fail to converge, when gene selection/pruning is inappropriate for the dataset, and where conclusions have not been validated for scATAC (most analyses focus on scRNA-seq).
