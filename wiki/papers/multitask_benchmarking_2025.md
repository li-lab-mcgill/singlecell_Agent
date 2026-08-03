---
paper_id: multitask_benchmarking_2025
title: "Multitask benchmarking of single-cell multimodal omics integration methods."
doi: "10.1038/s41592-025-02856-3"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12615258/"
source_ids: {doc_id: "pmc:12615258", pmid: "41083898", pmcid: "12615258", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "multi_batch_correction", "multi_cell_type_annotation"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["Find references defining kBET and LISI for assessing batch/mixing/integration quality of embeddings and neighbor graphs; report applicability to multi-omics modality-mixing assessment."]
extends: ["benchmark_multiome_2023", "benchmarking_joint_integration_2023"]
added: 2026-05-15
session: unknown
---

## Summary
This paper systematically benchmarks 40 single-cell multimodal integration methods across four integration categories (vertical, diagonal, mosaic, cross) and seven downstream tasks, using count data by default and modality-specific preprocessing (ATAC gene-activity or peak inputs). It provides per-category and per-task rankings, demonstrates dependence of method performance on task/metric/dataset complexity, and supplies an R Shiny app to explore and update results.

## Hypothesis framed
No single multimodal integration method will outperform others across all downstream tasks, modality combinations, and dataset complexities; therefore optimal method choice is task- and data-dependent.

## Questions answered
- Do integration method performances vary by downstream task, evaluation metric, and modality/batch complexity?
- Which methods produce better batch/mixing behavior (as measured by cLISI and ASW variants) across different multimodal modality combinations and integration categories?
- Which mixing/batch evaluation metrics are inapplicable or unreliable for certain output formats (e.g., graph-based outputs) or when cell-type labels are noisy?

## Key findings
Benchmarked 40 integration methods across 4 integration categories and 7 tasks; method rankings are highly metric- and task-dependent and no single method dominated across all tasks and datasets. Diagonal RNA–ATAC workflows used ATAC-derived gene-activity scores (Signac GeneActivity; Seurat CreateGeneActivityMatrix for one SNARE-seq sample lacking fragments), while vertical/mosaic/cross integrations used ATAC peak inputs by default. Mixing metrics explicitly used include cLISI and ASW variants; several metrics cannot be applied to graph-based outputs (ASW_cellType, iASW, ASW_batch, PCR). cLISI depended on accurate cell-type annotations, and the SCS spatial registration metric cannot distinguish methods that only perform linear transformations. Results are summarized into per-category/per-task overall rank scores and exposed via an R Shiny app.

## Methods used
Systematic benchmarking of 40 published integration methods grouped into four categories (vertical, diagonal, mosaic, cross); input defaults to count data, with ATAC gene-activity scores (Signac GeneActivity, Seurat CreateGeneActivityMatrix) for diagonal RNA–ATAC and ATAC peaks for other categories. Applied a battery of evaluation metrics per task including cLISI and ASW variants, principal component regression (PCR), SCS spatial registration metric, and computed overall rank scores per category/task. Produced interactive R Shiny application for result exploration and incremental updates.

## Method and dataset
Applied the benchmark pipeline to multiple multimodal single-cell datasets spanning RNA and ATAC modalities and various batch structures (exact dataset list and cell counts not specified in summary). Default preprocessing used count matrices; diagonal RNA–ATAC workflows used ATAC-derived gene-activity scores (Signac GeneActivity; Seurat CreateGeneActivityMatrix for an exceptional SNARE-seq sample). Experimental design: multi-task evaluation (7 tasks) across four integration categories for 40 methods; assumed methods accept either peak-level or gene-activity/ count inputs per their requirements.

## Limitations
Benchmark constrained by input-format mismatches (some methods require peaks, others require gene-activity scores), limited to the set of 40 methods and included datasets, and by evaluation-metric limitations: ASW_cellType, iASW, ASW_batch and PCR cannot be applied to graph-based outputs; cLISI and related label-dependent metrics require accurate cell-type annotations which may be unavailable or noisy; SCS spatial registration gives identical scores for methods that only perform linear transformations. The study did not provide original/definitive algorithmic definitions or parameterizations for kBET and LISI within the benchmark.

## Evidence pattern
comparison_design, effect_metric, validation, boundary_conditions

## Extends or contradicts
Extends prior benchmarking efforts of multimodal integration (e.g., benchmark_multiome_2023 and benchmarking_joint_integration_2023) by expanding the number of methods (40), integration categories, and downstream tasks and by providing per-task per-category rankings; does not report contradictions to those prior benchmarks but emphasizes task- and metric-dependence of conclusions.

## Boundary conditions
Works when: Applicable when input data are provided as count matrices and when methods accept the chosen input format (ATAC-derived gene-activity scores for diagonal RNA–ATAC integrations or ATAC peak matrices for vertical/mosaic/cross integrations). Label-dependent mixing metrics (cLISI) work when accurate cell-type annotations are available. Rankings are informative for the specific datasets, modality combinations, and tasks included in the benchmark.
Fails when: Mixing/batch metrics ASW_cellType, iASW, ASW_batch and PCR cannot be applied to graph-based method outputs. Label-dependent metrics (cLISI and similar) fail or provide misleading results when cell-type annotations are noisy or absent. The SCS spatial registration metric fails to discriminate methods that perform only linear transformations. Benchmark conclusions do not generalize to methods or datasets not included (e.g., methods that require input types not provided) and lack explicit kBET/LISI algorithmic parameterization for modality-mixing assessments.
