---
paper_id: epiconv_2022
title: "Joint analysis of scATAC-seq datasets using epiConv."
doi: "10.1186/s12859-022-04858-w"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9338487/"
source_ids: {doc_id: "pmc:9338487", pmid: "35906531", pmcid: "9338487", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_batch_correction", "multiomic_integration", "atac_differential_accessibility"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["What is the recommended preprocessing for scATAC-seq to mitigate depth bias for joint embedding (TF-IDF followed by LSI), and what failure modes or assumptions are known?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
This paper introduces epiConv, an algorithm that computes a library-size normalized cell–cell similarity from a binarized peak-by-cell matrix (M^T M), performs linear batch correction on top eigenvectors while retaining residuals, and uses the corrected similarity for joint analyses of scATAC-seq. The authors demonstrate improved batch correction and reduced over-fitting relative to existing workflows across PBMC, mouse brain, co-assay (ATAC–RNA) and hematopoiesis datasets, and show benefits for clustering and differential accessibility when single-dataset signal is weak.

## Hypothesis framed
A batch-correction method tailored to scATAC-seq that operates on a binarized peak-by-cell matrix similarity (M^T M) and corrects top eigenvectors while retaining residuals will remove technical batch effects without discarding biological signal, improving joint clustering, alignment of low-depth co-assay ATAC to high-quality references, and differential accessibility detection.

## Questions answered
- Does epiConv better correct batch effects and avoid over-fitting compared to existing methods on PBMC scATAC-seq collections?
- Can epiConv align low-depth co-assay scATAC-seq (paired ATAC–RNA) to high-quality ATAC references and increase chromatin-profile resolution?
- Does joint analysis with epiConv improve clustering and differential accessibility detection when biological signal is weak in single datasets?

## Key findings
On benchmarked PBMC datasets, epiConv produced superior batch correction and was less prone to over-fitting versus competing workflows. In mouse brain and co-assay data, epiConv aligned low-depth co-assay ATAC cells to high-quality ATAC references and increased the resolution of chromatin profiles. Using datasets of T cells (normal vs germ-free) and hematopoiesis (normal vs malignant), epiConv integrated across biological conditions and revealed cell populations that were not detectable when analyzing datasets individually. Retaining residuals after eigenvector-based correction preserved biological signals that other dimensionality-reduction-first methods discarded.

## Methods used
Binarization of peak-by-cell matrix; compute cell–cell similarity as M^T M; library-size normalization of similarity; eigen-decomposition of similarity matrix; linear batch correction applied to top r eigenvectors; retention of residuals after dimensionality reduction; downstream analyses on corrected similarity (clustering, alignment, differential accessibility). Benchmarking against alternative clustering and batch-correction workflows using metrics for batch mixing, over-fitting, clustering quality, and differential accessibility detection.

## Method and dataset
Method: epiConv (similarity-based batch correction on binarized peak-by-cell matrices with linear correction of top eigenvectors and retention of residuals). Data types and experimental designs: multiple scATAC-seq datasets including collections of PBMC samples, mouse brain datasets, co-assay (paired ATAC–RNA) low-depth data aligned to high-quality ATAC reference, and hematopoiesis datasets comparing normal and malignant samples; specific dataset sizes and cell counts not provided in the summary. Assumptions: input is binarized peak-by-cell matrix; library-size normalization suffices to control depth; major technical variation is captured in top eigenvectors; biological signal can be preserved in residuals after removing top eigenvector effects. Key parameter: number r of eigenvectors to correct.

## Limitations
Relies on binarized feature matrix and library-size normalization (other preprocessing schemes not evaluated); linear correction limited to top r eigenvectors so results depend on the choice of r; evaluations confined to PBMC, mouse brain, co-assay, and hematopoiesis datasets—scalability and robustness across all scATAC modalities, tissue types, and experimental designs not exhaustively tested; the paper does not provide direct recommendations or diagnostics for TF-IDF+LSI preprocessing, nor detailed guidance for selecting LSI components or TF/IDF formulations.

## Evidence pattern
entity_definition, comparison_design, statistical_unit, controls_covariates, validation, boundary_conditions

## Extends or contradicts
Extends prior batch-correction and integration approaches by providing an scATAC-specific similarity-based correction; contradicts the implicit assumption used by many scRNA-seq batch-correction tools that biological and technical variation are orthogonal by showing those approaches can over-fit on scATAC data.

## Boundary conditions
Works when: Input is a binarized peak-by-cell matrix with library-size normalization applied; batches share some overlapping cell types or a high-quality ATAC reference exists for alignment; technical variation is largely represented in top eigenvectors of the M^T M similarity matrix; datasets similar to tested collections (PBMCs, mouse brain, paired ATAC–RNA co-assay, hematopoiesis comparisons).
Fails when: When biological and technical variation are not separable by linear effects in the top r eigenvectors (e.g., technical effects distributed across many components), when preprocessing deviates from binarization/library-size normalization (e.g., TF-IDF+LSI pipelines not evaluated here), when r (number of eigenvectors) is chosen poorly leading to removal of true biology or insufficient correction, for very sparse or extremely low-depth scATAC profiles outside tested co-assay scenarios, and when applied to tissue types or scATAC modalities not represented in the benchmarks without further validation.
