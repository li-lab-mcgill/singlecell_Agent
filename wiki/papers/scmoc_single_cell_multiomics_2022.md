---
paper_id: scmoc_single_cell_multiomics_2022
title: "scMoC: single-cell multi-omics clustering."
doi: "10.1093/bioadv/vbac011"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9710707/"
source_ids: {doc_id: "pmc:9710707", pmid: "36699396", pmcid: "9710707", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "rna_clustering", "atac_clustering"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["What PBMC biological validation patterns were used in GLUE or similar RNA+ATAC co-embedding papers?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
scMoC is a clustering method for paired single-cell RNA-seq and ATAC-seq that imputes sparse ATAC profiles using RNA-derived cell neighborhoods and then merges independent RNA- and ATAC-based clusterings to produce integrated cell clusters. It demonstrates that RNA-guided imputation reduces ATAC sparsity and yields ATAC-derived clusters that better agree with RNA clustering and are supported by marker gene expression and motif/TF signals across multiple paired multi-omics datasets.

## Hypothesis framed
RNA-guided imputation of scATAC-seq profiles, using cell neighborhoods derived from paired scRNA-seq, reduces ATAC sparsity and improves joint clustering of cells measured with scRNA-seq and scATAC-seq compared with ATAC-only self-imputation.

## Questions answered
- Does RNA-guided imputation reduce scATAC sparsity and produce more separable ATAC-derived clusters than ATAC self-imputation?
- Does merging RNA and imputed-ATAC clusterings identify biologically meaningful cell groups across paired multi-omics protocols (sci-CAR, SNARE-seq, 10x multiome) including PBMC multiome?

## Key findings
RNA-guided imputation reduced measured scATAC zero fraction in the sci-CAR dataset from ~99.7% to ~89%. RNA-guided imputed ATAC profiles produced more separable ATAC-derived clusters that better agreed with RNA clusters than ATAC self-imputation. Merged scMoC clusters were supported by expression of known marker genes and ATAC-derived motif/TF signals and revealed RNA clusters that split based on accessibility differences. The approach produced biologically meaningful results across sci-CAR, SNARE-seq and 10x multiome PBMC data.

## Methods used
Seurat-like preprocessing (QC, normalization, log transform, variable gene selection, scaling, PCA), RNA-guided imputation using RNA-derived cell neighborhoods, ATAC self-imputation baseline, independent clustering of RNA and imputed ATAC, merging by splitting RNA clusters when ATAC provides evidence, UMAP visualization, cluster agreement metrics, motif/TF analysis for ATAC validation.

## Method and dataset
Method: scMoC, applied to paired scRNA-seq + scATAC-seq measured in the same cells. Data: publicly available paired datasets — sci-CAR (GSE117089), SNARE-seq (GSE126074), and 10x multiome PBMC (3k PBMC from 10x Genomics). Typical dataset sizes: thousands of cells (example: ~3,000 PBMC in 10x multiome). Experimental design: paired modalities per cell; independent clustering per modality followed by merging. Key assumption: local cell neighborhoods inferred from the less-sparse RNA modality are a better proxy for true cell similarity and can guide imputation of sparse ATAC signals.

## Limitations
Relies on the assumption that RNA-derived local neighborhoods reflect true cell similarity; can fail when modalities capture divergent biology (subpopulations differing only in RNA or only in accessibility). Imputation can introduce bias from the guiding modality. Performance depends on degree of ATAC sparsity and quality of RNA; generalization beyond the evaluated datasets and full comparison to all alternative integrative methods was not demonstrated.

## Evidence pattern
entity_definition, comparison_design, statistical_unit, effect_metric, validation, boundary_conditions, analysis_used

## Extends or contradicts
Extends prior integrated multimodal analysis approaches by introducing RNA-guided imputation of ATAC and a clustering-merging strategy (conceptually builds on integrated multimodal frameworks such as hao_2021-style approaches).

## Boundary conditions
Works when: Paired scRNA+scATAC measured in the same cells; RNA data is substantially less sparse and of sufficient quality to infer reliable local cell neighborhoods; datasets on the order of thousands of cells (e.g., 10x 3k PBMC); ATAC sparsity amenable to imputation (example: reduction from ~99.7% to ~89% zeros observed in sci-CAR).
Fails when: Modalities capture divergent biology (cell subpopulations differing only in RNA or only in accessibility), RNA quality is poor or too sparse to define neighborhoods, extreme ATAC sparsity that RNA cannot reliably impute, or when introducing cross-modal imputation bias is unacceptable; not validated for large variation in donor/batch covariates or for datasets outside the evaluated protocols.
