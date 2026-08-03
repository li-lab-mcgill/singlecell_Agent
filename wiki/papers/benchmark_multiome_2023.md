---
paper_id: benchmark_multiome_2023
title: "Benchmarking algorithms for joint integration of unpaired and paired single-cell RNA-seq and ATAC-seq data."
doi: "10.1186/s13059-023-03073-x"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC10594700/"
source_ids: {doc_id: "pmc:10594700", pmid: "37875977", pmcid: "", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "multi_cell_type_annotation", "multi_batch_correction"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["What evidence supports multimodal variational generative models for paired RNA+ATAC co-embedding and clustering on 10x Multiome-scale data?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
This paper benchmarks nine existing methods for joint integration of unpaired scRNA-seq and snATAC-seq with paired multiome (scRNA+ATAC) data using simulated splits from three public multiome datasets and one independent real-data task. It quantifies how multiome cell count, sequencing depth, batch effects, and incomplete cell-type overlap affect cell-type annotation accuracy and recovery of peak–gene associations, and identifies Seurat v4 and GLUE as top performers across scenarios.

## Hypothesis framed
Incorporating paired multiome (scRNA+ATAC) data into integration pipelines improves annotation of unpaired scRNA-seq and snATAC-seq and recovery of peak–gene relationships, and performance depends on multiome cell count, sequencing depth, batch effects, and choice of integration method.

## Questions answered
- Does integrating paired multiome data with unpaired scRNA-seq and snATAC-seq improve cell-type annotation accuracy compared to using single-modality data alone?
- How does the number of multiome cells versus per-cell sequencing depth affect cell-type annotation accuracy?
- Which integration methods perform best across scenarios that include complex batch effects and varying multiome representation?

## Key findings
Integrating multiome data improves annotation of scRNA-seq and snATAC-seq when the multiome contains a sufficient number of nuclei to represent the cell types present. Given a fixed budget, profiling more multiome cells yields better cell-type annotation than deeper sequencing per cell. Seurat v4 provided the best overall integration and annotation accuracy, especially under complex batch effects and when many multiome cells were available; GLUE performed comparably overall and outperformed Seurat v4 when the multiome dataset contained too few cells to resolve cell types. Multiome-guided integration aided discovery of peak–gene associations, but recovery depended on multiome representation and method choice. Results on an independent HPAP real-data task were consistent with simulated findings.

## Methods used
Benchmarking of nine integration methods (including Seurat v4 and GLUE) across five simulated scenarios and one real-data task; simulations derived from three public multiome datasets (PBMC, BMMC, SHARE-seq mouse skin). Performance evaluated using cell-type annotation accuracy and recovery of peak–gene associations; scenarios varied multiome cell count, per-cell sequencing depth, batch effects, and incomplete cell-type overlap.

## Method and dataset
Comparative evaluation of integration methods that jointly embed/integrate scRNA-seq, snATAC-seq, and paired multiome (scRNA+ATAC) data. Data sources: simulated unpaired splits generated from three published multiome datasets representing simple (PBMC), complex/multi-batch (BMMC), and large heterogeneous (SHARE-seq mouse skin) systems, plus an independent HPAP real-data task. Experimental design varied multiome cell numbers, sequencing depth per cell, batch effects, and cell-type overlap. Assumes paired multiome data can serve as a guide to align unpaired single-modality datasets and that simulated splits approximate real unpaired data.

## Limitations
Benchmarking limited to three public multiome datasets and simulated splits, so results may depend on dataset composition, annotation quality, and simulation choices. Only nine methods were tested; hyperparameter settings and implementation details can influence outcomes. Peak–gene association recovery and performance for very rare or novel cell types remain sensitive to multiome sampling. Generalizability to other tissues, technologies, or future methods is not exhaustively assessed. Explicit evaluations and hyperparameter details for multimodal variational autoencoder (VAE) models were not provided, nor were scalability/runtime benchmarks for VAE methods on 10x Multiome-scale data.

## Evidence pattern
comparison_design, effect_metric, validation, statistical_unit, boundary_conditions, controls_covariates, entity_definition

## Extends or contradicts
Extends prior work demonstrating that paired multiome measurements can inform integration of single-modality datasets by providing a controlled benchmark across multiple datasets and scenarios and ranking methods (identifying Seurat v4 and GLUE as top performers).

## Boundary conditions
Works when: Works when the multiome dataset contains a sufficient number of nuclei representing the cell types present; profiling more multiome cells (larger cell counts) is more beneficial than increasing per-cell sequencing depth for cell-type annotation; Seurat v4 is robust to complex batch effects when many multiome cells are available; multiome-guided integration can recover peak–gene links when cell types are adequately represented in the multiome.
Fails when: Fails or yields unreliable annotations and regulatory inferences when multiome representation is insufficient (too few multiome cells to represent cell types), for very rare or novel cell types poorly sampled in multiome data, under untested tissues/technologies, or when method-specific hyperparameters/implementations are suboptimal; VAE-style multimodal generative models' performance and scalability on large 10x Multiome-scale datasets were not explicitly validated and may fail under those untested conditions.
