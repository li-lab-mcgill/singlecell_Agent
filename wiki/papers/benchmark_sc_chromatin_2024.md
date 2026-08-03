---
paper_id: benchmark_sc_chromatin_2024
title: "Benchmarking computational methods for single-cell chromatin data analysis."
doi: "10.1186/s13059-024-03356-x"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC11328424/"
source_ids: {doc_id: "pmc:11328424", pmid: "39152456", pmcid: "11328424", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_clustering", "atac_cell_type_annotation", "multiomic_integration"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Find primary references that justify TF-IDF+SVD (LSI) for scATAC-seq and discuss depth correction and iterative LSI (e.g., in ArchR, Signac)."]
extends: ["glue_multimodal_2023"]
added: 2026-05-15
session: unknown
---

## Summary
This paper benchmarks eight feature-engineering pipelines (derived from five methods) for single-cell chromatin accessibility data across six published datasets using ten quantitative metrics at embedding, SNN-graph, and partition levels. It provides practical guidance showing that feature aggregation, SnapATAC, and SnapATAC2 generally outperform LSI-based pipelines, with method ranking depending on dataset complexity and scale.

## Hypothesis framed
Non-LSI feature-engineering pipelines (feature aggregation, SnapATAC, SnapATAC2) provide equal or better cell-type discovery and discrimination than LSI-based TF-IDF+SVD pipelines across realistic scATAC-seq and multi-omic datasets, with performance dependent on dataset complexity and scale.

## Questions answered
- Do feature aggregation, SnapATAC, and SnapATAC2 outperform LSI-based methods for cell-type discovery and discrimination in scATAC-seq and related multi-omic datasets?
- Which pipelines scale best and which are better at resolving rare or highly similar/subtype cell populations across datasets of varying complexity?

## Key findings
Tested eight pipelines from five methods on six published datasets with ten metrics: (1) Feature aggregation, SnapATAC, and SnapATAC2 consistently outperformed LSI-based methods across datasets and metrics. (2) For simple datasets with well-separated cell types, feature aggregation performed best and was especially effective at identifying small/rare cell classes; SnapATAC2 was typically the second-best. (3) For complex or hierarchical cell-type structures, SnapATAC and SnapATAC2 were superior at resolving fine-grained subtypes; feature aggregation sometimes failed to separate subtle subtypes. (4) SnapATAC and SnapATAC2 produced the best inferred gene activity scores. (5) For very large datasets, SnapATAC2 and ArchR were the most scalable. (6) ArchR and Signac were comparatively weaker at detecting rare populations. (7) Rankings depend on dataset complexity, parameter choices, and compute constraints.

## Methods used
Constructed end-to-end benchmarking pipeline starting from fragment/BED/BAM files and barcode-level QC; implemented eight feature-engineering pipelines derived from five published methods to produce cell embeddings; built shared nearest neighbor (SNN) graphs and Leiden clustering from each embedding; evaluated performance at embedding, SNN, and partition levels using ten metrics (including FOSCTTM for cross-modality alignment in an unpaired GLUE setup); systematically varied key parameter choices and tested sensitivity to dataset complexity, rarity, hierarchical structure, gene-activity inference, and computational scalability.

## Method and dataset
Benchmarked feature-engineering/dimensionality-reduction pipelines (including aggregation, LSI-based, SnapATAC, SnapATAC2, ArchR, Signac-derived pipelines) on scATAC-seq and related multi-omics fragment/BED/BAM inputs from six published datasets varying in protocol, tissue/species, coverage, and TSS enrichment; datasets ranged from small to very large (varied sizes unspecified). Assumptions: input is sparse, noisy, high-dimensional chromatin accessibility data and that existing pipeline implementations reflect typical user settings; cross-modality comparisons used an unpaired GLUE integration.

## Limitations
No perfect ground truth (annotations heterogeneous across datasets: RNA, genotype, FACS, tissue). Only six datasets and eight pipelines tested, so results may not generalize to all protocols or future method versions. Focused on a subset of parameter settings. Used an unpaired GLUE integration for cross-modality evaluation. Did not provide primary citations or derivations for TF-IDF+SVD (LSI), nor did it isolate or empirically compare the specific effects of depth-correction or iterative LSI implementations.

## Evidence pattern
comparison_design; statistical_unit: single cells; effect_metric: ten metrics at embedding/SNN/partition levels including FOSCTTM for cross-modality; validation: tested across six published datasets with parameter sweeps; boundary_conditions: reported sensitivity to dataset complexity, rarity, and scale

## Extends or contradicts
Extends glue_multimodal_2023 by using GLUE for unpaired cross-modality evaluation and provides broader benchmarking evidence; challenges the assumption that LSI-based TF-IDF+SVD pipelines are universally optimal for scATAC-seq by showing aggregation, SnapATAC, and SnapATAC2 often outperform LSI-based methods.

## Boundary conditions
Works when: Works when: datasets have well-separated cell types (feature aggregation excels and identifies rare/small populations); datasets have complex/hierarchical or highly similar subtypes (SnapATAC/SnapATAC2 excel at resolving fine-grained structure); datasets are very large and require scalability (SnapATAC2 and ArchR showed best scalability). Applies to fragment/BED/BAM-derived scATAC-seq and related multi-omic data with variable coverage and TSS enrichment.
Fails when: Fails when: method selection does not account for dataset complexity or parameter choices (rankings change with processing decisions); feature aggregation can fail to separate subtle/hierarchical subtypes; ArchR and Signac underperform at detecting rare populations; conclusions may not hold for datasets/protocols not represented in the six tested or for other parameter settings, and the study does not isolate impacts of depth-correction or iterative LSI so recommendations may miss benefits of those specific preprocessing steps.
