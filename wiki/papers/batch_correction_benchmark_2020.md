---
paper_id: batch_correction_benchmark_2020
title: "A benchmark of batch-effect correction methods for single-cell RNA sequencing data."
doi: "10.1186/s13059-019-1850-9"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC6964114/"
source_ids: {doc_id: "pmc:6964114", pmid: "31948481", pmcid: "6964114", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_batch_correction", "multi_batch_correction"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["Find references defining kBET and LISI for assessing batch/mixing/integration quality of embeddings and neighbor graphs; report applicability to multi-omics modality-mixing assessment."]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
This paper benchmarks 14 batch-effect correction methods for single-cell RNA-seq across five scenarios (identical cell types across technologies, non-identical cell types, multiple batches, large-scale, and simulated data) using ten real datasets and simulated data. It evaluates computational runtime, scalability, and correction efficacy using metrics including kBET, LISI, ASW, and ARI, and recommends Harmony, LIGER, and Seurat v3 as top choices, with Harmony preferred for its substantially shorter runtime.

## Hypothesis framed
Some existing batch-correction methods provide a superior balance of batch removal, preservation of cell-type purity, and scalability on diverse scRNA-seq datasets, and can be ranked empirically across realistic scenarios.

## Questions answered
- Which batch-correction methods best remove batch-driven variation while preserving cell-type purity across diverse scRNA-seq datasets and scenarios?
- Does Harmony achieve comparable integration accuracy to top methods while offering substantially shorter runtime and better scalability?

## Key findings
Across five benchmark scenarios and ten real datasets (plus simulations), Harmony, LIGER, and Seurat v3 were the top-performing methods overall in balancing batch mixing and cell-type structure while completing large-data runs. Harmony is recommended as the first method to try because it achieved comparable accuracy to the best methods but with substantially shorter runtime. ComBat, MMD-ResNet, and limma were among the poorest performers on these benchmarks. scGen performed better in supervised mode; scMerge performed reasonably in unsupervised mode.

## Methods used
Comparative benchmarking of 14 batch-correction methods (including Seurat v2/v3, Harmony, MNN/fastMNN, LIGER, ComBat, limma, scGen, scMerge, MMD-ResNet, and others). Preprocessing used recommended normalization, highly variable gene selection, and dimensionality reduction. Performance metrics: kBET, LISI, average silhouette width (ASW), adjusted Rand index (ARI), differential expression assessment, rank-sum aggregation; measured runtime and ability to complete large-data runs.

## Method and dataset
Benchmark applied to single-cell RNA-seq data across ten real datasets representing multiple technologies (10x, SMART-seq, Drop-seq, SMARTer), multiple tissues and species, plus simulated datasets. Experimental design included five scenarios: identical cell types across technologies, non-identical cell types, multiple batches, large-scale datasets, and simulated data. Methods were mostly run in unsupervised mode (scGen run supervised). Assumptions: input preprocessing (normalization, HVG selection, dimensionality reduction) and that batches share some overlapping biology in applicable scenarios.

## Limitations
Results depend on chosen preprocessing pipelines, parameter settings, and software versions; scGen was run in supervised mode while most methods were unsupervised, creating inconsistency; benchmark used a limited set of datasets and metrics that may not capture extreme heterogeneity or rare cell types; hardware and implementation differences affect runtime comparisons; newer methods released after the study were not included.

## Evidence pattern
entity_definition,comparison_design,effect_metric,statistical_unit,validation,boundary_conditions

## Extends or contradicts
Extends prior metric definitions and usage by Büttner et al. (kBET) and Korsunsky et al. (LISI) by empirically applying kBET and LISI across many batch-correction methods and datasets to characterize metric behavior and limitations in scRNA-seq integration benchmarks.

## Boundary conditions
Works when: Works when datasets are scRNA-seq with at least some overlapping cell types across batches; preprocessing includes normalization, HVG selection, and dimensionality reduction as recommended; evaluated scenarios include identical or partially overlapping cell-type compositions, multiple batches, and large datasets; when methods are applied mostly in unsupervised mode (except where supervised mode is explicitly used, e.g., scGen). Harmony is particularly suitable when computational resources are limited and runtime/scalability is a priority.
Fails when: Findings may not hold when batches have non-overlapping cell type compositions or extreme heterogeneity (rare cell types); when metric parameters (e.g., neighborhood size for kBET/LISI) are not tuned appropriately; for multi-omics modality-mixing (RNA+ATAC, CITE-seq) the paper did not evaluate applicability of kBET/LISI or methods, so conclusions do not extend to modality-specific neighbor graphs; results may not generalize to methods published after this study or to datasets with characteristics not represented in the ten real datasets used.
