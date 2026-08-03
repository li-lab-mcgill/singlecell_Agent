---
paper_id: benchmarking_joint_rna_atac_2023
title: "Benchmarking algorithms for joint integration of unpaired and paired single-cell RNA-seq and ATAC-seq data."
doi: "10.1186/s13059-023-03073-x"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC10594700/"
source_ids: {doc_id: "pmc:10594700", pmid: "37875977", pmcid: "", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "multi_cell_type_annotation", "atac_peak_to_gene"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["What are the statistical assumptions and validation metrics for Seurat v4 WNN joint RNA+ATAC embedding and clustering?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
This study benchmarks nine methods for integrating unpaired scRNA-seq and snATAC-seq with paired multiome (scRNA+ATAC) data across five simulated scenarios and one real dataset. It finds that incorporating multiome data improves cell-type annotation and peak–gene recovery when the multiome contains sufficient cells, and that Seurat v4 provides the best overall integration accuracy particularly under complex batch effects while GLUE can outperform Seurat v4 when multiome cell counts are too low.

## Hypothesis framed
Incorporating paired multiome data into integration of unpaired scRNA-seq and snATAC-seq improves cell-type annotation accuracy and recovery of peak–gene associations, and Seurat v4 WNN provides superior joint RNA+ATAC embeddings and clustering especially in the presence of complex batch effects.

## Questions answered
- Does adding paired multiome data improve annotation accuracy of unpaired scRNA-seq and snATAC-seq datasets?
- Is the number of multiome cells or the per-cell sequencing depth more important for accurate cell-type annotation given a fixed budget?
- Which integration method (Seurat v4 vs GLUE and others) yields the best annotation and peak–gene recovery under varying multiome representation and batch effects?

## Key findings
Incorporating multiome data improved annotation of scRNA-seq and snATAC-seq when the multiome dataset contained sufficient cells representing all cell types. The number of multiome cells was more important than per-cell sequencing depth for accurate cell-type annotation (profiling more cells preferred over deeper sequencing for a fixed budget). Seurat v4 achieved the best overall integration and annotation accuracy across simulated scenarios and a real HPAP task, especially with complex/multi-batch data and many multiome cells. GLUE performed comparably overall and outperformed Seurat v4 when the multiome dataset contained too few cells to resolve cell types. Multiome-guided integration aided discovery of peak–gene associations, but recovery depended on multiome representation and method choice. Benchmarks used three public multiome sources: PBMC (simple), BMMC (complex/multi-batch), and SHARE-seq mouse skin (large/heterogeneous).

## Methods used
Benchmarking of nine integration methods (including Seurat v4 and GLUE) using simulated splits from three public multiome datasets and one independent real dataset (HPAP). Simulations varied multiome cell count, per-cell sequencing depth, batch effects, and incomplete cell-type overlap. Performance metrics included cell-type annotation accuracy and recovery of peak–gene associations. Comparative analyses across five simulated scenarios and one real-data problem were performed.

## Method and dataset
Evaluated Seurat v4 WNN and other integration methods applied to scRNA-seq, snATAC-seq, and paired multiome (scRNA+ATAC) data. Datasets were derived from three public multiome experiments (PBMC, BMMC, SHARE-seq mouse skin) with simulated splits to create unpaired data; scenario parameters included varying multiome cell counts and per-cell sequencing depth. The paper did not provide formal/statistical distributional assumptions or theoretical derivation for Seurat v4's WNN modality-weighting scheme (this evidence is missing).

## Limitations
Benchmarking relied on three public multiome datasets and simulated splits, so results may depend on dataset composition, annotation quality, and simulation choices. Only nine methods were tested and parameter settings/implementations can influence outcomes. Peak–gene association recovery and performance on very rare or novel cell types are sensitive to multiome sampling; annotations and regulatory inferences can be unreliable when multiome representation is insufficient. Generalizability to other tissues, technologies, or future methods was not exhaustively assessed. Formal statistical assumptions and uncertainty quantification for Seurat v4 WNN were not reported.

## Evidence pattern
comparison_design, validation, boundary_conditions, effect_metric, controls_covariates, statistical_unit

## Extends or contradicts
Extends prior work demonstrating utility of multiome (paired) measurements for improving annotation of single-modality datasets; provides empirical support for Seurat v4's WNN integration approach as best-performing in many practical scenarios.

## Boundary conditions
Works when: Works when the multiome dataset contains a sufficient number of nuclei/cells to represent the cell types of interest; profiling more multiome cells is preferable to deeper per-cell sequencing for cell-type annotation under a fixed budget; Seurat v4 performs best in scenarios with complex batch effects and many multiome cells.
Fails when: Performance degrades when multiome representation is insufficient (too few multiome cells to resolve cell types); peak–gene association recovery and annotations are unreliable for very rare or novel cell types if multiome sampling is inadequate. In low multiome-cell regimes, GLUE can outperform Seurat v4. Results may not generalize to tissues, technologies, or parameter settings not represented in the three benchmarking datasets.
