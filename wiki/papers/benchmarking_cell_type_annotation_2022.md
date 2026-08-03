---
paper_id: benchmarking_cell_type_annotation_2022
title: "Benchmarking automated cell type annotation tools for single-cell ATAC-seq data."
doi: "10.3389/fgene.2022.1063233"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9792779/"
source_ids: {doc_id: "pmc:9792779", pmid: "36583014", pmcid: "", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_cell_type_annotation", "multiomic_integration", "multi_cell_type_annotation"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["What are the statistical assumptions and validation metrics for Seurat v4 WNN joint RNA+ATAC embedding and clustering?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
This paper benchmarks five automated cell type annotation methods (Conos, Seurat v3, scGCN, scJoint, Bridge integration) for label transfer from scRNA-seq to scATAC-seq across multiple mouse and human tissues. It evaluates classification accuracy (overall accuracy, weighted accuracy, macro F1), scalability (runtime, memory), and robustness to reduced reference size, label noise, sequencing depth, and presence of ATAC-unique cell types, finding Bridge integration to be the best overall performer.

## Hypothesis framed
Automated cell type annotation methods developed for scRNA-seq vary in accuracy and scalability when applied to scATAC-seq, and a multimodal Bridge integration approach will outperform other cross-modality label-transfer methods in accuracy and robustness.

## Questions answered
- Which cross-modality annotation method (among Conos, Seurat v3, scGCN, scJoint, Bridge integration) achieves the highest accuracy and robustness when transferring labels from scRNA-seq to scATAC-seq?
- How do annotation methods' performance change when reference size, label mislabeling rate, sequencing depth, and the number of ATAC-unique cell types are varied?

## Key findings
Bridge integration was the top performer across accuracy metrics and was robust to reduced reference size, high mislabeling rates (maintained performance up to ~70% mislabeled reference cells), and lower sequencing depth; it operates without gene-activity calculation but requires multimodal paired RNA+ATAC data. Conos was the fastest and most memory-efficient but had the lowest prediction accuracy. scJoint tended to assign query cells to similar/major cell types, performing well on coarse (major) annotations but poorly on deep/complex annotations. Seurat v3 and scGCN had moderate accuracy; scGCN was the slowest and in some settings performed near-random for ATAC-unique cell types. Most methods' accuracy remained stable once reference cell counts exceeded ~3,000 and most methods only showed major accuracy loss when reference mislabeling exceeded ~50% (except Bridge which remained robust). All methods degraded substantially under large reductions in sequencing depth.

## Methods used
Benchmarking of five label-transfer methods (Conos, Seurat v3, scGCN, scJoint, Bridge integration) on publicly available single-cell datasets (mouse and human: brain, lung, kidney, PBMC, BMMC). Metrics computed: overall accuracy, weighted accuracy, macro F1, plus ATAC-specific metrics. Experiments varied reference cell counts, mislabeling rates, sequencing depth, and number of ATAC-unique cell types. Runtime and memory usage were recorded. Bridge integration used multimodal paired data; other methods used gene-activity calculations or embedding-based transfers.

## Method and dataset
Applied Conos, Seurat v3, scGCN, scJoint, and Bridge integration to scATAC-seq query and scRNA-seq reference datasets drawn from public human and mouse tissues (brain, lung, kidney, PBMC, BMMC). Experiments included BMMC as a primary benchmark and varied reference sizes (stability reported for reference cell counts >= ~3,000), simulated mislabeling up to ~70%, downsampled sequencing depth, and introduced ATAC-unique cell types. Assumptions: Bridge integration requires paired multimodal (RNA+ATAC) data and avoids gene-activity transformation; other methods assume gene activity links between chromatin accessibility and gene expression or rely on embedding alignment procedures.

## Limitations
Top performance of Bridge integration depends on availability of multimodal paired data which is often unavailable. Benchmarking covered a limited set of public datasets and five methods; results may differ on other tissues, protocols, preprocessing choices, or hyperparameter settings. The study did not exhaustively evaluate different gene-activity transformations or all integration pipelines. Detailed Seurat v4 WNN statistical assumptions, parameter settings, and WNN-specific validation metrics were not reported in this benchmarking.

## Evidence pattern
comparison_design, validation, boundary_conditions, effect_metric, statistical_unit, controls_covariates, analysis used

## Extends or contradicts
Extends prior scRNA-seq label-transfer and integration work by systematically benchmarking five cross-modality methods for transferring scRNA-seq labels to scATAC-seq and by quantifying robustness to reference size, label noise, sequencing depth, and ATAC-unique cell types.

## Boundary conditions
Works when: Bridge integration works when paired multimodal (RNA+ATAC) data are available; methods' performance is stable when reference cell counts exceed ~3,000; Bridge remains robust to reference mislabeling up to approximately 70% and to moderate reductions in sequencing depth; scJoint performs well when target annotations are coarse/major-cell-type labels.
Fails when: Most methods lose major accuracy when reference mislabeling exceeds ~50% (except Bridge); all methods degrade substantially under large reductions in sequencing depth; scGCN may perform near-random for ATAC-unique cell types; scJoint performs poorly on datasets with deep/complex annotations; Bridge cannot be applied when multimodal paired data are not available.
