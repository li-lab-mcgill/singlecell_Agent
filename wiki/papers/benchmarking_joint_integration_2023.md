---
paper_id: benchmarking_joint_integration_2023
title: "Benchmarking algorithms for joint integration of unpaired and paired single-cell RNA-seq and ATAC-seq data."
doi: "10.1101/2023.02.01.526609"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9915567/"
source_ids: {doc_id: "pmc:9915567", pmid: "36778447", pmcid: "", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "multi_cell_type_annotation", "atac_peak_to_gene"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["What evidence supports multimodal variational generative models for paired RNA+ATAC co-embedding and clustering on 10x Multiome-scale data?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
This paper benchmarks seven methods for jointly integrating paired 10x Multiome (RNA+ATAC) and unpaired single-modality datasets, using PBMC and BMMC public multiome datasets to assess annotation accuracy, peak–gene recovery, and robustness to batch effects. It finds multiome-guided integration improves annotation when the multiome reference is sufficiently large, and that Seurat v4 outperformed VAE-based multimodal methods (MultiVI, Cobolt) across the benchmarks.

## Hypothesis framed
Multiome-guided integration methods, including VAE-based multimodal generative models (MultiVI/Cobolt), will improve cell type annotation and peak–gene recovery for unpaired scRNA-seq and snATAC-seq when combined with paired 10x Multiome data, and the number of multiome cells is a stronger determinant of annotation accuracy than per-cell sequencing depth.

## Questions answered
- Do VAE-based multimodal methods (MultiVI, Cobolt) outperform Seurat v4 for integrating paired 10x Multiome with unpaired scRNA-seq and snATAC-seq for cell-type annotation and peak–gene recovery?
- Does adding multiome data improve annotation of single-modality scRNA-seq and snATAC-seq datasets, and how do multiome cell count and per-cell sequencing depth affect annotation accuracy?
- How robust are integration methods (including Seurat v4, MultiVI, Cobolt) to complex batch effects across donors/sites in multiome-scale datasets?

## Key findings
1) Incorporating multiome data improves annotation of scRNA-seq and snATAC-seq only when the multiome dataset contains enough cells to reveal cell-type identities (demonstrated on PBMCs and complex BMMCs). 2) The number of multiome cells is more critical than per-cell sequencing depth for accurate cell-type annotation—profiling more cells is preferable under budget constraints. 3) Seurat v4 achieved the best integration and annotation accuracy across benchmarks, including under complex batch effects and donor/site variation. 4) VAE-based multimodal methods (MultiVI, Cobolt) did not outperform Seurat v4 on annotation, peak–gene recovery, or batch-effect robustness in these datasets. 5) Treating multiome modalities as separate unpaired datasets ('multiome-split') controls for cell-count effects in comparisons.

## Methods used
Head-to-head benchmarking of seven methods: Seurat v4 (including a supervised projection and an 'integrate' variant), LIGER, FigR, bindSC (unpaired-style) and MultiVI, Cobolt (multiome-guided VAE methods). Used two public 10x Multiome datasets (PBMC and BMMC), simulated unpaired scenarios by splitting multiome into separate modalities, varied multiome cell counts and per-cell sequencing depth, and evaluated annotation accuracy, peak–gene association recovery, and behavior under batch effects.

## Method and dataset
Applied Seurat v4, LIGER, FigR, bindSC, MultiVI, and Cobolt to 10x Genomics Multiome paired RNA+ATAC data: a PBMC dataset (simple, seven well-separated cell types) and a BMMC dataset (complex hematopoietic populations across multiple donors/sites). Experimental design included creating unpaired datasets, a 'multiome-split' control to match cell counts, and systematic downsampling/upsampling to test effects of multiome cell count versus per-cell sequencing depth. Assumes multiome reference is representative of the cell types in unpaired data and that methods can be compared on the evaluated metrics without exhaustive tuning of all hyperparameters.

## Limitations
Benchmarks used only two public datasets (PBMC and BMMC), which may not generalize to other tissues or protocols; simulation of unpaired data by splitting multiome may not capture real experimental variability; results depend on preprocessing and parameter choices that were not exhaustively explored; runtime/memory scalability and detailed VAE hyperparameters/training regimes were not reported; other downstream tasks (trajectory inference, regulatory network reconstruction) were not comprehensively evaluated.

## Evidence pattern
entity_definition, comparison_design, statistical_unit, effect_metric, controls_covariates, validation, boundary_conditions

## Extends or contradicts
Extends benchmarking literature by evaluating VAE-based multimodal methods (MultiVI, Cobolt) on paired 10x Multiome datasets and controls for cell-count effects; contradicts the expectation that VAE multimodal methods necessarily outperform supervised-projection approaches (Seurat v4) for annotation and peak–gene recovery on these datasets.

## Boundary conditions
Works when: Works when the multiome reference contains sufficient cells to represent all cell types in the unpaired data (e.g., PBMC-like datasets with clearly separated cell types or sufficiently large BMMC multiome references); on 10x Multiome-scale data similar to the PBMC and BMMC datasets used; when the primary objective is cell-type annotation or peak–gene association recovery and a supervised projection reference (Seurat v4) is available.
Fails when: Fails or underperforms when the multiome dataset is too small to reveal cell-type identities (insufficient cell counts to capture rare types), when tissues or technical protocols differ substantially from PBMC/BMMC, when unpaired experimental variability is high and not simulated by splitting, or for downstream tasks not evaluated (e.g., trajectory inference, regulatory network reconstruction); VAE methods may not outperform supervised references in these failure modes.
