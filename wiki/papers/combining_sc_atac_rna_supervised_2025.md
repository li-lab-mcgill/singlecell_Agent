---
paper_id: combining_sc_atac_rna_supervised_2025
title: "Combining single-cell ATAC and RNA sequencing for supervised cell annotation."
doi: "10.1186/s12859-025-06084-6"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC11863512/"
source_ids: {doc_id: "pmc:11863512", pmid: "40011801", pmcid: "11863512", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multi_cell_type_annotation", "multiomic_integration", "rna_cell_type_annotation"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["What biological validation and expected structures does the Seurat v4 WNN paper establish for paired scRNA+scATAC PBMC datasets?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
This study tests whether adding single-cell ATAC-seq to single-cell RNA-seq improves supervised cell-type annotation using paired 10x multiome PBMC and neuronal datasets. It shows that multimodal input (RNA+ATAC) increases F1 and prediction confidence for PBMC subtype annotation when using scVI embeddings, with largest gains in T cell subtypes (especially CD4 effector memory), but finds no benefit in a neuronal (Alzheimer's) dataset.

## Hypothesis framed
Combining scATAC with scRNA feature sets improves supervised cell-type annotation accuracy in 10x multiome PBMC data, and this improvement depends on embedding choice (nonlinear scVI vs linear PCA) and cell type.

## Questions answered
- Does adding scATAC to scRNA improve supervised cell-type annotation accuracy for PBMC multiome datasets?
- Does the choice of embedding method (scVI vs PCA) change whether ATAC adds value for supervised annotation?
- Does adding ATAC improve supervised annotation for neuronal (Alzheimer's) multiome datasets?

## Key findings
Using scVI embeddings, combining RNA+ATAC increased F1 scores and prediction confidence across random forest, SVM, and logistic regression classifiers for PBMC subtype annotation; the largest improvement was observed for CD4 T effector memory cells and T cell subtypes generally, while dendritic cells showed the smallest improvement. No improvement from adding ATAC was observed in the neuronal (Alzheimer's) multiome dataset. The ATAC-derived benefit largely disappeared when the classification task was restricted to major PBMC cell types.

## Methods used
Paired 10x Genomics multiome data; dimensionality reduction via PCA and scVI (nonlinear autoencoder); supervised classifiers: random forest, support vector machine, logistic regression; evaluation metrics: F1 score, prediction confidence, silhouette scores, UMAP visualization; statistical assessment via bootstrap resampling.

## Method and dataset
Applied PCA and scVI embeddings to RNA and ATAC features derived from paired 10x Genomics multiome datasets: human PBMCs and neuronal cells from Alzheimer's disease samples (dataset sizes not specified in summary). Compared supervised classification (RF, SVM, LR) of RNA-only versus combined RNA+ATAC feature sets across embeddings with bootstrap resampling. Assumes accurate cell-type labels for supervised training and that embeddings capture cross-modal signal without excessive overfitting.

## Limitations
ATAC benefit depended strongly on embedding method (observable with scVI, variable with PCA); results are dataset- and cell-type-specific (no benefit in neuronal dataset); only conventional embeddings (PCA, scVI) and classical classifiers were tested; potential confounders include sequencing noise, zero inflation in single-cell data, and risk of overfitting from high-capacity autoencoders; no direct evaluation of Seurat v4 WNN outputs or per-cell modality weight outputs.

## Evidence pattern
comparison_design: RNA-only vs RNA+ATAC across embeddings (PCA, scVI) and classifiers (RF, SVM, LR); statistical_unit: single cells evaluated with bootstrap resampling; metric: F1 score (primary), prediction confidence, silhouette scores, UMAP visual inspection; validation: biological validation on PBMC multiome showing subtype-specific gains (largest for CD4 effector memory); boundary_conditions: embedding-dependent and dataset/cell-type-specific effects; analysis used: dimensionality reduction, supervised classification, bootstrap statistics, visualization.

## Extends or contradicts
Extends prior reports that multimodal (RNA+ATAC) data improve unsupervised annotation by demonstrating supervised annotation gains in PBMC subtypes under specific embedding conditions; refines prior expectations by showing no benefit in a neuronal (Alzheimer's) multiome dataset and strong dependence on embedding choice.

## Boundary conditions
Works when: Works when: paired 10x multiome PBMC data are available and scVI (nonlinear autoencoder) embeddings are used; classification into fine-grained PBMC subtypes (not just major types); classifiers such as RF, SVM, or logistic regression trained with bootstrap resampling; cell types include T cell subtypes (notably CD4 effector memory) where chromatin accessibility adds discriminative signal.
Fails when: Fails or provides no observable benefit when: dataset is neuronal multiome (Alzheimer's) as tested; only linear embeddings (PCA) are used (ATAC gains variable or absent); task is coarse-grained annotation of major PBMC cell types (benefit largely disappears); data exhibit high sequencing noise, extreme zero-inflation, or when scVI overfits due to limited data or high model capacity; no evaluated evidence for WNN-specific outputs (modality weights, WNN graphs).
