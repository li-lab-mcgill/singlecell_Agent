---
paper_id: joint_rna_atac_benchmark_2023
title: "Benchmarking algorithms for joint integration of unpaired and paired single-cell RNA-seq and ATAC-seq data."
doi: "10.1101/2023.02.01.526609"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9915567/"
source_ids: {doc_id: "pmc:9915567", pmid: "36778447", pmcid: "", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "multi_cell_type_annotation", "multi_batch_correction"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["What are the statistical assumptions and validation metrics for Seurat v4 WNN joint RNA+ATAC embedding and clustering?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
This paper benchmarks seven methods for joint integration of paired (multiome) and unpaired scRNA-seq and snATAC-seq data using two public multiome datasets (PBMC and BMMC). It measures ability to recover peak–gene links and to improve cell-type annotation under varying multiome cell counts, sequencing depth, and batch-effect scenarios, finding that Seurat v4 performs best overall.

## Hypothesis framed
Incorporating paired multiome data when integrating with unpaired scRNA-seq and snATAC-seq improves cell-type annotation and peak–gene recovery, and Seurat v4's WNN/supervised projection approach will outperform other integration methods, including under batch effects, provided the multiome reference contains sufficient cells.

## Questions answered
- Does incorporating multiome (paired) data improve annotation accuracy of unpaired scRNA-seq and snATAC-seq datasets?
- Is the number of multiome cells or per-cell sequencing depth more important for accurate cell type annotation when integrating multiome with single-modality data?
- Does Seurat v4 outperform MultiVI and Cobolt in integrating scRNA, snATAC, and multiome data, including in the presence of complex batch effects?

## Key findings
1) Incorporating multiome data improves cell-type annotation of scRNA-seq and snATAC-seq when the multiome dataset contains enough cells to reveal cell-type identities. 2) The number of multiome cells is more critical than per-cell sequencing depth for accurate cell-type annotation (profiling more cells to capture rare types is preferable under budget constraints). 3) Across the PBMC (7 well-separated cell types) and BMMC (complex hematopoietic populations with batch effects) benchmarks, Seurat v4 achieved the best integration and annotation accuracy and was most robust to complex batch effects. 4) MultiVI and Cobolt did not outperform Seurat v4 in these evaluations. 5) Treating multiome modalities as separate unpaired datasets ('multiome-split') helped control for cell-count effects in comparisons.

## Methods used
Benchmarking comparison of seven integration methods (Seurat v4 [including a Seurat v4 integrate variant], LIGER, FigR, bindSC, MultiVI, Cobolt) using two public multiome datasets (PBMC and BMMC). Simulations included splitting multiome into unpaired modalities, subsampling multiome cell counts, varying per-cell sequencing depth, and introducing batch/donor effects. Evaluations used cell-type annotation accuracy, recovery of peak–gene associations, and behavior under batch effects as metrics.

## Method and dataset
Applied Seurat v4 WNN/supervised projection and five other integration frameworks to integrate scRNA-seq, snATAC-seq, and multiome (paired) data. Data: two public multiome datasets — PBMCs (simple benchmark with seven well-separated cell types) and bone marrow mononuclear cells (BMMCs; complex hematopoietic populations with multiple sites/donors). Experimental design: simulated unpaired vs guided integrations, multiome-split control, varied multiome cell counts and per-cell ATAC/RNA sequencing depth, and tested batch-effect scenarios. Assumptions of Seurat v4 WNN (statistical/noise/distributional assumptions, independence, modality-weight derivation) are not explicitly provided in the paper summary.

## Limitations
Benchmarks rely on two public multiome datasets (PBMC and BMMC) that may not represent all tissues or experimental protocols. Simulated 'multiome-split' unpaired scenarios may not capture real unpaired variability. Performance depends on preprocessing, parameter choices, and implementations not exhaustively explored. Evaluation focused on cell-type annotation and peak–gene associations; other downstream tasks were not comprehensively assessed. Newer method versions released after the study could change results.

## Evidence pattern
comparison_design, statistical_unit, effect_metric, controls_covariates, validation, boundary_conditions

## Extends or contradicts
Extends prior benchmarking/comparative studies of single-cell integration by evaluating joint integration of paired multiome and unpaired single-modality data; does not report direct contradictions of prior findings that multiome data can improve annotation of single-modality datasets.

## Boundary conditions
Works when: Works when the multiome reference contains sufficient cells to reveal all relevant cell types (including rare types); demonstrated on PBMCs (seven well-separated cell types) and complex BMMC hematopoietic populations. Profiling more multiome cells (rather than deeper sequencing per cell) improves cell-type annotation under fixed budgets. Seurat v4 WNN/supervised projection performs best when the multiome-derived reference is sufficiently large.
Fails when: Performance degrades when the multiome reference is too small to capture cell-type diversity (insufficient cells), when experimental scenarios differ substantially from PBMC/BMMC protocols, or when preprocessing/hyperparameter choices are suboptimal. Methods other than Seurat v4 perform worse under complex batch effects or limited multiome cell counts. Explicit statistical assumptions and per-parameter sensitivity (e.g., WNN k, dimensionality) are not reported, limiting formal uncertainty quantification.
