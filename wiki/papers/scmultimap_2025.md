---
paper_id: scmultimap_2025
title: "scMultiMap: Cell-type-specific mapping of enhancers and target genes from single-cell multimodal data."
doi: "10.1038/s41467-025-59306-z"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12033308/"
source_ids: {doc_id: "pmc:12033308", pmid: "40287418", pmcid: "12033308", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_peak_to_gene", "multi_grn_inference"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Find computational strategies for connecting noncoding AD GWAS risk variants to cell-type-specific scATAC peaks, genes, and regulatory programs, including validation and failure modes."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
scMultiMap is a statistical method for inferring cell-type-specific enhancer-gene associations from paired single-cell RNA-seq and ATAC-seq counts. It uses a joint latent-variable model with sequencing-depth and confounder adjustment, moment-based estimation, and analytical p-values to scale peak-gene testing. In Alzheimer's disease analyses, inferred links produced strong GWAS heritability enrichment in microglia, supporting use of paired multiome data to connect noncoding AD risk variants to regulatory target genes.

## Hypothesis framed
A joint latent-variable model of paired single-cell gene expression and chromatin accessibility counts can identify cell-type-specific enhancer-gene associations with better calibration, power, robustness to technical confounding, and computational efficiency than existing approaches.

## Questions answered
- Does scMultiMap control type I error while maintaining higher power for enhancer-gene association testing in sparse paired scRNA-seq/scATAC-seq data?
- Does scMultiMap outperform Signac and SCENT in reproducibility, external support, and computational efficiency on blood and brain multimodal datasets?
- Do scMultiMap-derived enhancer-gene links in Alzheimer's disease data show GWAS heritability enrichment in disease-relevant brain cell types such as microglia?

## Key findings
scMultiMap showed well-calibrated type I error, higher statistical power, and robustness to sequencing-depth variation and sample-level confounding compared with Signac and SCENT. Its computational cost was reported as less than 1% of existing methods in benchmarking. In real blood and brain data, scMultiMap recovered more reproducible and externally supported enhancer-gene pairs, and in Alzheimer's disease analysis it produced the highest GWAS heritability enrichment in microglia.

## Methods used
The paper used a joint latent-variable model for paired single-cell RNA and ATAC counts, sequencing-depth and confounder adjustment, moment-based parameter estimation, analytical p-value derivation for peak-gene association tests, simulation benchmarking, real-data benchmarking in blood and brain multiome datasets, comparison against Signac and SCENT, reproducibility analysis, validation against external evidence, and integration of inferred enhancer-gene links with Alzheimer's disease GWAS heritability enrichment.

## Method and dataset
scMultiMap was applied to sparse paired single-cell multimodal data measuring gene expression and chromatin accessibility in the same cells, including simulated datasets and real blood and brain datasets. It tests pairwise associations between candidate chromatin-accessible peaks and genes within cell types. The method assumes paired RNA and ATAC measurements from the same cells, cell-type annotations suitable for cell-type-specific analysis, and candidate peak-gene pairs to test; exact cell counts and sample sizes are not provided in the summary.

## Limitations
scMultiMap infers pairwise peak-gene associations and does not by itself prove causal enhancer-target regulation. Performance depends on single-cell multiome data quality, coverage, and cell-type annotation, and sparse data may limit detection in rare cell types or for weak regulatory effects. The method is designed primarily for paired scRNA-seq/scATAC-seq data, so unpaired designs or other modalities may require adaptation. It does not fully model transcription-factor programs, higher-order enhancer interactions, or context-specific multi-enhancer regulation, and inferred links require experimental perturbation validation.

## Evidence pattern
The evidence combines entity definition of enhancer-gene pairs, comparison design against Signac and SCENT, single-cell peak-gene association tests as the statistical unit, type I error, statistical power, reproducibility, external support, computational cost, and GWAS heritability enrichment as metrics, adjustment for sequencing depth and other confounders as covariates, validation in blood and brain multimodal datasets, and Alzheimer's disease GWAS enrichment analysis in brain cell types including microglia.

## Extends or contradicts
The paper extends prior single-cell enhancer-gene mapping approaches such as Signac and SCENT by replacing correlation or resampling-heavy procedures with a joint latent-variable model, moment-based estimation, and analytical p-values for sparse paired multiome counts. It does not directly contradict a specific prior wiki paper based on the provided summary.

## Boundary conditions
Works when: Works when gene expression and chromatin accessibility are measured in the same cells using paired scRNA-seq/scATAC-seq multiome assays, candidate peak-gene pairs can be defined, cell-type labels are available for cell-type-specific testing, and sequencing-depth or sample-level confounders need adjustment.
Fails when: May fail or lose power for rare cell types, weak enhancer-gene effects, low-coverage or poor-quality multiome data, incorrect cell-type annotations, unpaired RNA and ATAC datasets without adaptation, causal claims requiring perturbation evidence, and regulatory mechanisms involving multiple enhancers, transcription factors, or higher-order interactions not represented by pairwise peak-gene tests.
