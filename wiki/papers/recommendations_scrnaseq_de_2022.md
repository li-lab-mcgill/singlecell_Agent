---
paper_id: recommendations_scrnaseq_de_2022
title: "Recommendations of scRNA-seq Differential Gene Expression Analysis Based on Comprehensive Benchmarking."
doi: "10.3390/life12060850"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9225332/"
source_ids: {doc_id: "pmc:9225332", pmid: "35743881", pmcid: "9225332", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_differential_expression"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Identify what statistical unit of inference credible studies use for disease-associated cell-type-specific differential expression/accessibility in single-cell or single-nucleus datasets with donors, and what failure modes arise if cells are treated as independent."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This paper developed a simulator for multi-subject, multi-condition scRNA-seq differential expression analysis that models cell-to-cell variation within subjects, subject-to-subject variation, cell type effects, library size effects, covariates, and group effects. It benchmarked 12 DE methods on simulated 10x Genomics-style data and evaluated top methods on multiple sclerosis and lung fibrosis scRNA-seq datasets, concluding that negative-binomial mixed-model approaches, especially NEBULA-HL and glmmTMB, are preferable for cell-type-specific disease or treatment DE.

## Hypothesis framed
In multi-subject, multi-condition scRNA-seq differential expression analysis, methods that model negative-binomial counts with subject-level variation will control error rates and recover disease or treatment effects better than cell-level or pseudo-bulk approaches that do not adequately account for within-subject cell dependence.

## Questions answered
- Do negative-binomial mixed-model methods outperform cell-level and pseudo-bulk differential expression methods for multi-subject, multi-condition scRNA-seq data?
- Which scRNA-seq differential expression methods maintain type I error and false discovery rate control while preserving power, AUROC, and PRAUC in simulated donor-replicated 10x Genomics-style experiments?
- Do NEBULA-HL and glmmTMB identify more biologically relevant disease-associated DEGs than DESeq2 in real multiple sclerosis and lung fibrosis scRNA-seq datasets?

## Key findings
Negative-binomial mixed-model methods, particularly NEBULA-HL and glmmTMB, generally outperformed the other benchmarked DE methods across simulated multi-subject, multi-condition scRNA-seq settings. NEBULA-HL showed strong power, AUROC, and PRAUC while maintaining reasonable type I error and FDR behavior in key settings. In real-data analyses, NEBULA-HL and glmmTMB produced highly overlapping DEG lists and detected biologically relevant signals missed by DESeq2; in the multiple sclerosis dataset both detected validated genes including PPIA and CUX2, whereas DESeq2 missed them. Gene set enrichment analysis indicated that NEBULA-HL DEGs had stronger enrichment for relevant GO biological processes.

## Methods used
The authors built a simulator for 10x Genomics-style multi-subject, multi-condition scRNA-seq data with cell-level, subject-level, gene-level, cell-type, library-size, group, and covariate effects and flexible gene mean-dispersion relationships. They benchmarked 12 differential expression methods, including cell-level methods and pseudo-bulk methods, using type I error, FDR, power, AUROC, PRAUC, fold-change bias, fold-change correlation, and computation time. They applied NEBULA-HL, glmmTMB, and DESeq2 to a multiple sclerosis dataset from Schirmer et al. and a lung fibrosis dataset from Reyfman et al., comparing DEG overlap, volcano plots, and GO biological process enrichment.

## Method and dataset
The main data type was multi-subject, multi-condition 10x Genomics-style scRNA-seq. Simulations were parameterized to resemble real scRNA-seq datasets and included multiple subjects, multiple conditions, cell types, covariates, library size variation, within-subject cell-to-cell variation, and between-subject variation; exact sample sizes and cell counts are not provided in the summary. Real validation used two scRNA-seq datasets: multiple sclerosis from Schirmer et al. and lung fibrosis from Reyfman et al. The recommended methods assume count-based gene expression data with overdispersion and a donor-replicated experimental design in which subject-level variation should be modeled rather than treating all cells as independent replicates.

## Limitations
The benchmark used simulated data derived from selected real datasets and focused mainly on 10x Genomics-style multi-subject, multi-condition experiments, so results may not generalize to all scRNA-seq platforms, study designs, or biological systems. Real-data validation was limited to two non-Alzheimer's datasets and a subset of biologically relevant cell types. Some methods showed dataset-dependent behavior, including deflated error rates in certain lung-data simulations. The conclusions depend on simulator assumptions about expression distributions, covariate effects, subject effects, mean-dispersion relationships, and filtering strategies.

## Evidence pattern
The paper used a comparison-design benchmark in which the statistical unit of inference was the subject or donor in multi-condition scRNA-seq, with within-subject cells modeled as dependent observations. It compared 12 DE methods using simulated datasets with known group effects and covariates, evaluated error control and power metrics, then validated selected methods on two real disease datasets with DEG overlap and GO biological process enrichment. The evidence supports subject-aware negative-binomial mixed models over methods that inadequately account for donor-level variation.

## Extends or contradicts
This paper extends prior scRNA-seq DE benchmarking by using a simulator that explicitly includes multi-subject experimental structure, within-subject cell dependence, subject-to-subject variation, cell-type variation, library size effects, covariates, and group effects. It supports the broader finding that treating cells as independent replicates is inappropriate for disease-associated cell-type-specific DE in donor-replicated single-cell studies.

## Boundary conditions
Works when: Works when analyzing count-based scRNA-seq differential expression in multi-subject, multi-condition designs with biological replication at the donor or subject level, especially 10x Genomics-style data where cell types are analyzed for disease or treatment effects and covariates or library size effects may be present. The recommendation is most directly supported for settings resembling the simulations and the two real datasets: multiple sclerosis and lung fibrosis scRNA-seq.
Fails when: The findings may not apply to single-nucleus ATAC-seq, chromatin accessibility testing, non-10x platforms, study designs without donor-level biological replication, or real datasets that strongly violate the simulator assumptions about count distributions, mean-dispersion relationships, covariate effects, subject effects, and filtering. Methods that treat cells as independent experimental units are expected to fail when many cells come from the same subject because they ignore within-subject dependence and can produce poorer error control or less reliable disease-effect detection.
