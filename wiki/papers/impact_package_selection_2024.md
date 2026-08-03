---
paper_id: impact_package_selection_2024
title: "The impact of package selection and versioning on single-cell RNA-seq analysis."
doi: "10.1101/2024.04.04.588111"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC11014608/"
source_ids: {doc_id: "pmc:11014608", pmid: "38617255", pmcid: "11014608", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_clustering", "rna_differential_expression"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["What are the statistical assumptions and validation metrics for Seurat v4 WNN joint RNA+ATAC embedding and clustering?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
This study quantifies how choice of software (Seurat v5.0.2 vs Scanpy v1.9.5) and package versioning affect outputs of standard scRNA-seq workflows using 10x PBMC datasets. It shows substantial differences at HVG selection, PCA, clustering, and differential expression that can be comparable in magnitude to major reductions in sequencing depth or cell sampling, emphasizing the need for reproducible computational environments.

## Hypothesis framed
The choice of single-cell analysis software package and specific package versions (Seurat vs Scanpy) materially alter intermediate and final outputs of standard scRNA-seq workflows, producing differences comparable to substantial experimental perturbations (e.g., downsampling reads or cells).

## Questions answered
- How much do Seurat v5.0.2 and Scanpy v1.9.5 default workflows differ at each pipeline step (filtering, normalization, HVG selection, PCA, clustering, differential expression)?
- To what extent can aligning algorithms/parameters reduce differences between Seurat and Scanpy, and do version differences still cause discrepancies (especially in differential expression)?
- How does variability introduced by package choice compare in magnitude to experimental changes such as downsampling reads or removing cells?

## Key findings
Filtering and log-normalization produce equivalent outputs when given identical input matrices. Under default settings, HVG selection Jaccard index between Seurat and Scanpy was ~0.22, propagating to PCA differences (up to 0.1 absolute difference in variance explained by PC1 and ~30° separation between PC2 eigenvectors) and downstream clustering and differential expression discrepancies. Many differences were reduced by aligning methods/parameters, but distinct package versions still produced considerable discrepancies, particularly in differential expression. The magnitude of variability between package defaults was comparable to downsampling to <5% of reads or removing ~20% of cells.

## Methods used
Comparative analysis of Seurat v5.0.2 and Scanpy v1.9.5 on 10x PBMC datasets; count matrices generated with kb-python and Cell Ranger; ran standard pipelines with default settings and runs aligning function arguments/inputs; stepwise inspection of outputs (filtering, log-normalization, HVG selection, PCA, clustering, differential expression); quantified set overlap using Jaccard indices; compared PCA eigenvectors and variance explained including angles between PCs; simulated read/cell downsampling to contextualize effect sizes; code and computational environments captured via Docker/conda.

## Method and dataset
Method: side-by-side comparison of Seurat v5.0.2 and Scanpy v1.9.5 standard scRNA-seq workflows. Data: 10x Genomics PBMC 10k (primary) and PBMC 5k (validation) cell-by-gene count matrices generated via kb-python and Cell Ranger; ~10,000 and ~5,000 cells respectively. Experimental design: default vs parameter-aligned pipeline runs, per-step output comparisons. Assumptions: analyses assume count matrices as starting input (constructed by kb-python/Cell Ranger), that HVG/PCA/clustering methods operate under their default algorithmic assumptions; does not assume or evaluate multimodal WNN-specific statistical models.

## Limitations
Analysis limited to PBMC 10k and PBMC 5k datasets and to specific package versions (Seurat v5.0.2, Scanpy v1.9.5); results may not generalize to other data types, technologies, newer or other versions, or to non-default parameter choices. Did not address construction choices for count matrices (e.g., nascent vs mature transcripts) or best effect-size measures for sparse single-cell data. Did not evaluate Seurat v4 WNN joint RNA+ATAC algorithm or WNN-specific validation metrics.

## Evidence pattern
comparison_design; statistical_unit=cells; metrics=Jaccard index for gene sets, PCA variance explained, angles between PC eigenvectors, clustering labels; validation=read-and-cell downsampling simulations and PBMC 5k validation dataset; covariates=package version and parameter settings; boundary_conditions=documented version/parameter sensitivity; analysis=stepwise pipeline comparisons with aligned vs default settings.

## Extends or contradicts
Contradicts the common assumption that Seurat and Scanpy default pipelines produce comparable results by demonstrating substantial differences across steps; extends literature on reproducibility and the impact of software versioning on computational biology analyses.

## Boundary conditions
Works when: Applies when analyzing 10x Genomics PBMC datasets of ~5k–10k cells using Seurat v5.0.2 and Scanpy v1.9.5 standard pipelines; when count matrices are identically constructed (kb-python/Cell Ranger) and inputs/parameters are aligned, filtering and log-normalization outputs are equivalent and many differences can be reduced.
Fails when: Findings may not hold for other data types (non-PBMC), other technologies or multiomic datasets (RNA+ATAC), for newer or different package versions, or when non-default methods/parameters or different count-matrix construction choices are used. The study does not provide WNN-specific assumptions or validation metrics for joint RNA+ATAC embedding/clustering; differential expression is particularly sensitive to versioning and may fail to be consistent across versions.
