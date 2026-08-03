---
paper_id: integrating_scrna_scatac_intertype_gnn
title: "Integrating scRNA-seq and scATAC-seq with inter-type attention heterogeneous graph neural networks."
doi: "10.1093/bib/bbae711"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC11725394/"
source_ids: {doc_id: "pmc:11725394", pmid: "39800872", pmcid: "11725394", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "multi_grn_inference", "atac_peak_to_gene"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Find foundational descriptions and validations of: (1) per-cell modality-weighted shared-nearest-neighbor joint embedding for paired RNA+ATAC; (2) multimodal variational autoencoder with shared+private factors for paired and unpaired RNA+ATAC; (3) graph-regularized joint embedding using prior gene–peak links."]
extends: ["hao_2021"]
added: 2026-05-15
session: unknown
---

## Summary
scMI is a heterogeneous graph neural network that models cells, genes and ATAC peaks as distinct node types and uses an inter-type attention mechanism plus subgraph sampling to learn data-driven cross-modality links (gene–peak) and shared embeddings. It produces embeddings that improve ATAC→RNA and RNA→ATAC prediction, cell clustering and gene regulatory network inference versus several baseline methods, and enables better integration of unmatched multi-omics datasets without relying on motif databases.

## Hypothesis framed
A heterogeneous graph neural network that models cells, genes and peaks with an inter-type attention mechanism can learn cross-modality (gene–peak) relationships directly from single-cell RNA+ATAC data and produce embeddings that outperform or match database-reliant methods for modality prediction, clustering, GRN inference and unmatched data integration.

## Questions answered
- Does a data-driven heterogeneous graph neural network (scMI) that learns gene–peak links from the data outperform motif/database-reliant methods for ATAC→RNA and RNA→ATAC prediction across benchmark single-cell datasets?
- Can learned cross-modality embeddings from scMI improve alignment and downstream GRN inference when integrating unmatched single-cell RNA and ATAC datasets compared with database-reliant approaches?

## Key findings
For ATAC→RNA prediction scMI achieved the lowest average RMSE and highest PCC overall (best RMSE in 7/8 datasets; highest PCC in 5/8 datasets). For RNA→ATAC prediction scMI achieved best RMSE and ranked second by PCC, and attained the highest average AUROC in 5/8 datasets. scMI-produced embeddings preserved biological signal and yielded improved clustering and gene regulatory network inference relative to baseline methods (LS.Lab, Cajal, scJoint, scMoGNN) on multiple matched datasets including PBMCs and NeurIPS challenge sets.

## Methods used
Constructed a heterogeneous graph with node types for cells, genes and peaks; frequency-based random-walk-with-restart subgraph sampling; heterogeneous graph convolutions with an inter-type attention mechanism; collaborative learning strategy jointly optimizing embeddings with downstream objectives (modality prediction, clustering, GRN inference). Benchmarked against LS.Lab, Cajal, scJoint, scMoGNN using RMSE, Pearson correlation (PCC), AUROC and ARI.

## Method and dataset
Method: scMI heterogeneous graph neural network (cells, genes, peaks), inter-type attention, subgraph sampling, joint optimization with downstream losses. Data: multiple matched single-cell paired RNA+ATAC datasets (including PBMCs and NeurIPS challenge datasets); evaluation performed across 8 datasets for modality prediction tasks. Exact per-dataset cell counts and total cells not reported in the summary. Assumptions: input can be paired or unpaired RNA+ATAC (method supports unmatched integration), preprocessing and feature selection enable graph construction, computational resources sufficient for graph construction and subgraph sampling.

## Limitations
Computational and hyperparameter complexity introduced by graph construction and subgraph sampling; sensitivity to preprocessing choices and sparsity of single-cell data; limited external experimental validation of newly learned regulatory links; generalization to very large, highly heterogeneous tissues or rare cell types was not fully explored; interpretability of learned cross-modality relationships relative to established biology may require further biological follow-up.

## Evidence pattern
entity_definition, comparison_design, validation (benchmarking), metrics (RMSE, PCC, AUROC, ARI), datasets (PBMCs, NeurIPS sets; 8 datasets reported for modality prediction), subgraph_sampling analysis, boundary_conditions reported

## Extends or contradicts
Extends prior motif/database-reliant integration approaches (e.g., WNN-style ideas from hao_2021) by learning cross-modality gene–peak links directly from data and contrasts with methods that require motif/peak–gene databases.

## Boundary conditions
Works when: Works when paired or unpaired single-cell RNA+ATAC datasets are available where cross-modality links can be inferred from data; when dataset sizes and feature counts are amenable to frequency-based subgraph sampling; demonstrated superior ATAC→RNA RMSE in 7/8 benchmark datasets and superior PCC in 5/8 datasets; tested on PBMC and NeurIPS challenge datasets.
Fails when: Fails or degrades when single-cell data are extremely sparse or heavily noisy, when preprocessing is suboptimal, when computational resources are insufficient for graph construction/subgraph sampling, for very large highly heterogeneous tissues or extremely rare cell types (generalization not fully validated), and when external experimental validation of predicted gene–peak links is required but not available.
