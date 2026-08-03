---
paper_id: benchmark_crossomics_rna_atac_2026
title: "A comprehensive benchmarking study on computational tools for cross-omics label transfer from single-cell RNA to ATAC data."
doi: "10.1093/g3journal/jkag026"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC13042286/"
source_ids: {doc_id: "pmc:13042286", pmid: "41655240", pmcid: "13042286", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_cell_type_annotation", "multi_cell_type_annotation", "multiomic_integration"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Find foundational descriptions and validations of per-cell modality-weighted shared-nearest-neighbor joint embedding for paired RNA+ATAC; multimodal variational autoencoder with shared+private factors for paired and unpaired RNA+ATAC; and graph-regularized joint embedding using prior gene–peak links, and to extract boundary conditions, failure modes, and dataset scales"]
extends: ["benchmark_multiome_2023", "benchmarking_joint_integration_2023", "benchmarking_joint_rna_atac_2023"]
added: 2026-05-15
session: unknown
---

## Summary
Comprehensive benchmark of 27 computational tools for transferring cell-type labels from scRNA-seq to scATAC-seq across multiple human and mouse tissues, comparing 5 direct label-transfer methods and 22 joint-embedding approaches. Identifies top-performing tools (Bridge and GLUE with paired multimodal data; GLUE and bindSC without paired data), documents common failure modes (data imbalance, cross-omics dissimilarity, binarization, semi-supervision), and reports runtime/peak-memory scalability.

## Hypothesis framed
Methods that utilize paired multimodal data or explicit region-to-gene graph priors (e.g., Bridge, GLUE) provide superior accuracy and scalability for cross-omics label transfer from scRNA to scATAC compared to methods that do not leverage paired data or peak-level information.

## Questions answered
- Do methods that use high-quality paired multimodal data outperform others for RNA->ATAC label transfer?
- Which algorithms are most accurate and scalable for cross-omics label transfer across diverse human and mouse tissues (paired vs unpaired settings)?
- How do data properties — imbalance, cross-omics cell-type dissimilarity, binarization, and semi-supervised training — affect label-transfer performance?

## Key findings
27 methods evaluated (5 direct label-transfer, 22 joint-embedding). When high-quality paired multimodal data were available, Bridge and GLUE (multi) had the best label-transfer performance. Without paired data, GLUE and bindSC achieved the highest prediction accuracy on shared cell types (GLUE top in most non-paired tasks). Top-performing methods used peak-level ATAC information rather than only gene-activity matrices. Data imbalance, cross-omics dissimilarity of shared cell types, binarization of input data, and introducing semi-supervised strategies generally degraded performance. Bridge and deep-learning approaches (e.g., GLUE) were among the most time- and memory-efficient. For ATAC-specific cell-type prediction, graph- or deep-learning-based approaches (e.g., scGCN) showed relatively strong performance. Joint-embedding evaluation used latent representations (default or 20 dims) with a kNN classifier (k=30).

## Methods used
Benchmark of 27 computational tools: 5 direct label-transfer methods and 22 joint-embedding methods. For joint-embedding, latent embeddings (default or 20 dimensions) were extracted and a kNN classifier (k=30) trained on scRNA embeddings to predict scATAC labels. Inputs included raw counts, gene-activity matrices, or peak-level matrices as required. Region-to-gene links used GLUE's guidance-graph when needed. Benchmarks covered multiple human and mouse tissues/atlases, tested paired and unpaired settings, assessed accuracy on shared vs ATAC-specific cell types, tested effects of imbalance, cross-omics dissimilarity, binarization, semi-supervision, and measured runtime and peak CPU memory across dataset sizes.

## Method and dataset
Applied each method to scRNA-seq and scATAC-seq data (raw counts, gene-activity matrices, or peak-level matrices) drawn from multiple human and mouse tissues and atlases; used available paired multimodal datasets when applicable and unpaired transfers otherwise. Joint-embedding methods used default latent dimensionality or 20 dims; predictions used a kNN (k=30) classifier trained on scRNA embeddings. Region-to-gene priors for methods that require them were generated using GLUE's guidance-graph and appropriate reference genomes. Exact per-dataset cell counts and resource numbers were not reported in the summary.

## Limitations
Benchmarks run with default or recommended settings and a fixed kNN classifier, so results may change with parameter tuning or alternative classifiers; only a selected set of tissues/datasets were tested and may not capture all experimental variability or batch effects; methods requiring paired multimodal data were only evaluable on a subset of tasks; generating region-to-gene priors required reference genomes which may limit generality; hyperparameter sensitivity, architecture/training details for deep models (e.g., multiVI) and exhaustive classifier sweeps were not explored; exact dataset scales and per-method resource consumption numbers were not reported in the summary.

## Evidence pattern
comparison_design, validation, effect_metric, boundary_conditions, statistical_unit (methods compared across multiple datasets/tissues; latent dims and kNN classifier fixed; accuracy assessed separately for shared and ATAC-specific cell types; runtime and peak-memory measured across dataset sizes; failure modes tested via simulated or real imbalance, cross-omics dissimilarity, binarization, and semi-supervised variants).

## Extends or contradicts
Extends prior benchmarking work (benchmark_multiome_2023, benchmarking_joint_integration_2023, benchmarking_joint_rna_atac_2023) by evaluating a larger set of 27 tools across additional tissues and explicit tests of failure modes; confirms prior findings that graph- and deep-learning-based integration methods (GLUE, scGCN) are strong performers and that utilizing peak-level ATAC information improves transfer.

## Boundary conditions
Works when: High-quality paired multimodal (RNA+ATAC) reference data are available for transfer — Bridge and GLUE perform best in this setting; methods that can directly use peak-level ATAC input (not only gene-activity matrices) perform better; deep-learning methods like GLUE and Bridge scale efficiently in time and memory; joint-embedding with latent dims ≈20 and kNN classifier (k≈30) produced reliable comparative results in this benchmark.
Fails when: Performance degrades when reference/target datasets have strong class imbalance, when shared cell types show high cross-omics dissimilarity, when ATAC inputs are binarized, or when semi-supervised training strategies are introduced; methods that require paired multimodal data cannot be applied when such paired data are absent; region-to-gene-prior-based methods fail or are limited if appropriate genome-based priors/links are unavailable or incorrect; results sensitive to choice of hyperparameters and classifier (benchmarks used default settings).
