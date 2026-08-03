---
paper_id: scananse_2023
title: "scANANSE gene regulatory network and motif analysis of single-cell clusters."
doi: "10.12688/f1000research.130530.1"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC10728588/"
source_ids: {doc_id: "pmc:10728588", pmid: "38116584", pmcid: "10728588", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multi_grn_inference", "atac_motif_analysis", "rna_grn_inference"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Map method classes for TF activity and regulatory network inference from single-cell multiome data and identify their assumptions/failure modes."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This paper introduces scANANSE, a software pipeline that connects Seurat or Scanpy single-cell objects to ANANSE gene regulatory network inference and GimmeMotifs motif enrichment analysis. It applies the workflow to clustered single-cell RNA and ATAC data from a public PBMC multi-omics dataset and returns transcription-factor influence scores and motif-enrichment results to the original single-cell object for visualization and interpretation.

## Hypothesis framed
ANANSE and GimmeMotifs can be adapted from bulk-data workflows to clustered single-cell RNA-seq and ATAC-seq data to recover biologically meaningful, cell-type-specific transcription-factor regulators and motif enrichments.

## Questions answered
- Can a cluster-level ANANSE workflow using single-cell RNA and ATAC data identify known cell-type-specific hematopoietic transcription factors in PBMC multiome data?
- Can scANANSE compare each cell cluster against an average network from all clusters to rank influential transcription factors per cluster?
- Can combining scANANSE with GimmeMotifs support prediction of transcription factors with activating and repressing roles in gene regulation?

## Key findings
In a public PBMC multi-omics demonstration, scANANSE recovered known hematopoietic, cell-type-specific transcription factors and highlighted expected regulators such as the monocyte-associated factor SPI1. The study concluded that the pipeline can rank influential transcription factors per cluster and that combining scANANSE with GimmeMotifs can help predict both activating and repressing transcription-factor roles.

## Methods used
The workflow uses AnanseSeurat or AnanseScanpy to export TPM-normalized expression, differentially expressed genes, and ATAC peak counts from Seurat or Scanpy objects. The Snakemake workflow anansnake runs ANANSE gene regulatory network comparisons, typically comparing each cluster against an average network derived from all clusters. In parallel, gimme maelstrom performs transcription-factor motif enrichment analysis, and the resulting transcription-factor influence scores and motif outputs are imported back into the single-cell object.

## Method and dataset
Method: scANANSE pipeline for clustered single-cell RNA-seq and ATAC-seq or joint multiome data, using ANANSE for gene regulatory network inference and GimmeMotifs for motif enrichment. Dataset: publicly available PBMC multi-omics dataset. Experimental design: cluster-level comparisons, typically each PBMC cluster versus an average network from all clusters. Assumptions: input data are preprocessed, quality-controlled, clustered, and either joint multi-omic data or matched RNA and ATAC objects with shared cluster labels or reliable label transfer.

## Limitations
The demonstration is limited to a public PBMC multi-omics dataset and does not include broad benchmarking across tissues, disease contexts, perturbations, or experimental platforms. The paper does not systematically compare scANANSE against methods such as SCENIC+, FigR, chromVAR, or other TF activity and GRN inference tools. It reports computational predictions of transcription-factor influence and motif enrichment, which require experimental validation. Performance depends on accurate preprocessing, quality control, clustering, RNA-ATAC integration, and shared cluster labels when RNA and ATAC data are stored in separate objects.

## Evidence pattern
Entity definition of scANANSE as an ANANSE/GimmeMotifs-based workflow; comparison design using cluster-versus-average-network contrasts; statistical unit is the single-cell cluster rather than individual cells; effect metric includes transcription-factor influence scores and motif-enrichment outputs; validation is qualitative recovery of known hematopoietic transcription factors in PBMC clusters; boundary conditions include requirement for preprocessed, clustered RNA and ATAC data with aligned cluster labels.

## Extends or contradicts
This paper extends the bulk-data ANANSE gene regulatory network analysis and GimmeMotifs motif-enrichment workflows to clustered single-cell RNA-seq and ATAC-seq or multiome data. It does not directly extend or contradict any listed existing wiki paper.

## Boundary conditions
Works when: Works when single-cell RNA and ATAC data have already been quality-controlled, normalized or otherwise preprocessed, clustered, and represented in standard Seurat or Scanpy objects. For separate RNA and ATAC objects, the method requires shared cluster labels or reliable label transfer. The demonstrated use case is PBMC multi-omics data with cluster-level comparisons against an all-cluster average network.
Fails when: May fail or produce misleading regulatory predictions when clustering is inaccurate, RNA and ATAC modalities are misaligned, shared labels are unavailable for separate assays, label transfer is unreliable, or preprocessing and quality control are poor. The paper does not establish robustness to sparse ATAC profiles, strong batch effects, motif redundancy, incorrect peak calling, rare cell types, or datasets outside the demonstrated PBMC setting.
