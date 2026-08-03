---
paper_id: cell_type_specific_mapping_2024
title: "Cell-type-specific mapping of enhancers and target genes from single-cell multimodal data."
doi: "10.1101/2024.09.24.614814"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC11463474/"
source_ids: {doc_id: "pmc:11463474", pmid: "39386519", pmcid: "11463474", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_peak_to_gene", "multiomic_integration"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Find computational strategies for connecting noncoding AD GWAS risk variants to cell-type-specific scATAC peaks, genes, and regulatory programs, including validation and failure modes."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This paper introduces scMultiMap, a statistical method for inferring cell-type-specific enhancer-gene associations from paired single-cell multimodal RNA and ATAC count data. It matters for disease genetics because it links noncoding GWAS-associated regulatory elements to putative target genes in relevant cell types while explicitly modeling sparsity and sequencing-depth confounding.

## Hypothesis framed
A joint latent-variable model of paired single-cell RNA and ATAC counts that estimates latent peak-gene covariance while adjusting for sequencing depth can identify enhancer-gene associations with better error control, power, reproducibility, external regulatory concordance, and computational efficiency than existing methods.

## Questions answered
- Does scMultiMap control type I error while improving power for enhancer-gene association testing in sparse paired single-cell RNA and ATAC data?
- Are scMultiMap peak-gene links more reproducible across independent blood and brain multimodal datasets and more consistent with orthogonal regulatory evidence than links from Signac or SCENT?
- Can scMultiMap applied to postmortem Alzheimer's disease brain multimodal data identify cell types, peaks, and genes enriched for AD GWAS heritability?

## Key findings
scMultiMap showed appropriate type I error control and higher statistical power than Signac and SCENT in systematic analyses of blood and brain data. Its inferred enhancer-gene associations were more reproducible across independent datasets and more consistent with orthogonal regulatory modalities, while its computational cost was reported to be less than 1% of existing methods. In postmortem Alzheimer's disease brain multimodal data, scMultiMap produced the highest AD GWAS heritability enrichment in microglia and identified candidate microglial regulatory mechanisms for AD-associated variants.

## Methods used
The authors used a joint latent-variable model in which observed RNA and ATAC counts are modeled as Poisson measurements of latent gene expression and latent chromatin accessibility. The enhancer-gene association parameter is the covariance between latent accessibility at a candidate peak and latent expression of a candidate gene. The method adjusts for cell-specific sequencing depth, uses moment-based estimation, derives analytic p-values, and was evaluated against Signac and SCENT using simulations, real blood and brain single-cell multimodal datasets, reproducibility analyses, orthogonal regulatory-evidence concordance, computational-cost benchmarking, and GWAS heritability enrichment analysis.

## Method and dataset
scMultiMap was applied to paired single-cell multimodal datasets measuring RNA expression and chromatin accessibility in the same cells, including blood datasets, brain datasets, and postmortem brain samples from Alzheimer's disease patients and controls. The method assumes that RNA and ATAC observed counts are sparse Poisson observations of latent biological expression and accessibility levels, that sequencing-depth variation can be explicitly modeled as a technical confounder, and that latent peak-gene covariance is evidence for enhancer-gene association.

## Limitations
scMultiMap infers statistical association between chromatin accessibility and gene expression and does not prove causal enhancer-gene regulation. The Alzheimer's disease results are hypothesis-generating and do not establish functional effects of individual GWAS variants. The method focuses on pairwise peak-gene associations and may not capture combinatorial transcription-factor effects, long-range chromatin contacts, nonlinear regulation, or context-dependent enhancer logic. Performance depends on the quality, depth, and cell-type annotation of paired single-cell multimodal datasets.

## Evidence pattern
The paper supports its claims through method definition, comparison design against Signac and SCENT, peak-gene pair association tests as the statistical unit, latent covariance and analytic p-values as effect/statistical metrics, sequencing-depth adjustment as a covariate/control, simulations for type I error and power, real blood and brain datasets for reproducibility, orthogonal regulatory modalities for validation, computational-cost benchmarking, and AD GWAS heritability enrichment in cell-type-specific enhancer-gene maps.

## Extends or contradicts
This paper extends prior single-cell enhancer-gene mapping approaches such as Signac and SCENT by replacing correlation-style or computationally intensive testing with a sequencing-depth-adjusted joint latent-variable count model and analytic p-values. It does not directly contradict a specific existing wiki paper listed here.

## Boundary conditions
Works when: Works when paired single-cell multimodal RNA-seq and ATAC-seq are measured in the same cells, cell-specific sequencing depth can be estimated, candidate peak-gene pairs can be tested within defined cell types, and cell-type annotations are reliable. It is especially intended for sparse multimodal count data where technical depth variation would confound naive accessibility-expression correlations.
Fails when: Does not directly apply to unpaired scATAC-only datasets or scRNA-only datasets without matched RNA and ATAC measurements in the same cells. It may fail or lose power in low-quality or shallow multimodal datasets, inaccurate cell-type annotations, settings requiring causal inference for individual variants, allele-specific accessibility or expression modeling, transcription-factor combinatorial regulatory programs, or enhancer-gene mechanisms mediated by chromatin contacts not captured by pairwise latent covariance.
