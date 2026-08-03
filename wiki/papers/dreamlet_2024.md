---
paper_id: dreamlet_2024
title: "Efficient differential expression analysis of large-scale single cell transcriptomics data using dreamlet."
doi: "10.1101/2023.03.17.533005"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC10055252/"
source_ids: {doc_id: "pmc:10055252", pmid: "36993704", pmcid: "10055252", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_differential_expression"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Identify what statistical unit of inference credible single-cell disease-control studies use for differential molecular state claims, and what failure modes arise if cells are treated as independent replicates."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This paper introduces dreamlet, an open-source R package for differential expression analysis in large single-cell and single-nucleus RNA-seq studies using subject-level pseudobulk profiles within cell clusters. It fits precision-weighted linear mixed models to control false positives while supporting repeated measures, replicates, batch effects, and large cohort-scale datasets.

## Hypothesis framed
A subject-level pseudobulk approach using precision-weighted linear mixed models can provide scalable, false-positive-controlled differential expression testing across cell clusters in large single-cell and single-nucleus RNA-seq cohorts.

## Questions answered
- Does modeling subject-by-cell-cluster pseudobulk expression with precision-weighted linear mixed models control false positive rates for differential expression in large multi-subject single-cell RNA-seq data?
- Can dreamlet scale differential expression analysis to datasets with hundreds to thousands of donors and millions of cells while using less time and memory than existing workflows?
- Can a pseudobulk mixed-model framework support complex study designs including repeated measures, biological or technical replicates, and high-dimensional batch effects?

## Key findings
Dreamlet controlled false positive rates while maintaining high power for differential expression testing across subjects and cell clusters. In benchmarking, it computed pseudobulk counts for 1000 donors across 12 cell types totaling 2.2 million cells in about 10 minutes using approximately 20 GB of memory. The method was demonstrated on published datasets and on 1.4 million postmortem brain nuclei from 150 Alzheimer's disease cases and 149 controls.

## Methods used
The authors aggregated single-cell counts into pseudobulk profiles by subject and cell cluster, then fit gene- and cell-cluster-specific precision-weighted linear mixed models. Precision weights were initialized from an approximate Poisson count model and refined using an empirical mean-variance trend based on the limma-voom framework. The workflow extended empirical Bayes moderated t-statistics to precision-weighted linear mixed models and used parallel processing, on-disk H5AD storage, and Bioconductor/SingleCellExperiment integration.

## Method and dataset
Dreamlet was applied to single-cell and single-nucleus RNA-seq count data aggregated by donor and cell cluster. Benchmarks included 1000 donors, 12 cell types, and 2.2 million cells; an Alzheimer's disease application used 1.4 million single nuclei from postmortem brains of 150 cases and 149 controls. The method assumes the donor or subject is the statistical unit of inference, cell clusters or cell-type annotations are accurate, enough cells are available per subject-cluster combination to estimate pseudobulk expression, and the specified mixed model captures relevant covariates, batch effects, and repeated-measure structure.

## Limitations
Dreamlet analyzes average expression per subject and cell cluster rather than modeling all cell-level variability directly. Its reliability depends on accurate cell clustering or cell-type annotation and sufficient cells per subject and cluster. Very large cohorts or highly complex mixed models may still require substantial computational resources. The provided summary gives limited detail on biological findings from the Alzheimer's disease application.

## Evidence pattern
The paper supports its claims using a subject-level statistical unit: counts are aggregated by subject and cell cluster before differential expression testing. The comparison design evaluates disease or trait associations across subjects within each cell cluster, with support for covariates, repeated measures, biological or technical replicates, and batch effects. Validation consisted of benchmarking false positive rate control, power, runtime, memory use, and scalability on published datasets plus a 1.4 million-nucleus Alzheimer's disease case-control dataset.

## Extends or contradicts
This paper extends pseudobulk differential expression practice for multi-subject single-cell RNA-seq by adding precision-weighted linear mixed models, empirical Bayes moderation, support for complex designs, and computational optimizations for cohort-scale datasets. It contradicts analyses that treat individual cells as independent replicates for subject-level disease-control claims because such analyses do not use the donor as the unit of inference and can inflate false positives.

## Boundary conditions
Works when: Works when the goal is cell-cluster-specific differential expression across subjects in scRNA-seq or snRNA-seq data; when samples include multiple donors or subjects; when subject-level covariates, repeated measures, replicates, or batch effects need to be modeled; and when each subject-cluster combination has enough cells and read depth to form informative pseudobulk profiles.
Fails when: Does not directly model cell-level expression heterogeneity beyond subject-cluster averages. Performance can degrade when cell-type annotations or clusters are inaccurate, when many subject-cluster combinations have too few cells, when the model omits important confounders or batch effects, or when the scientific question requires single-cell-level rather than subject-level inference. Treating cells as independent replicates instead of aggregating by subject risks false-positive inflation and invalid subject-level disease-control inference.
