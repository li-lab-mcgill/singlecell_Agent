---
paper_id: screni_2025
title: "ScReNI: Single-cell Regulatory Network Inference Through Integrating scRNA-seq and scATAC-seq Data."
doi: "10.1093/gpbjnl/qzaf060"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12646639/"
source_ids: {doc_id: "pmc:12646639", pmid: "40591481", pmcid: "12646639", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multi_grn_inference", "rna_grn_inference", "atac_grn_inference"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Map method classes for TF activity and regulatory network inference from single-cell multiome data and identify their assumptions/failure modes."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
ScReNI is a computational method for inferring cell-specific gene regulatory networks by integrating scRNA-seq and scATAC-seq data, including paired and unpaired datasets. It uses nearest-neighbor cell selection and a modified random forest to infer nonlinear regulatory relationships between gene expression and chromatin accessibility, then uses inferred networks for clustering, cell type-specific network inference, and cell-enriched regulator identification.

## Hypothesis framed
Integrating single-cell gene expression and chromatin accessibility with nearest-neighbor aggregation and nonlinear random-forest modeling will infer more accurate cell-specific regulatory networks than existing cell-specific network inference methods.

## Questions answered
- Does ScReNI outperform CSN, LIONESS, and CeSpGRN for network-based clustering of cell types from single-cell RNA-seq and ATAC-seq data?
- Can ScReNI infer cell type-specific regulatory networks from paired or unpaired scRNA-seq and scATAC-seq data?
- Can cell-specific networks inferred by ScReNI identify cell-enriched regulators?

## Key findings
ScReNI inferred regulatory relationships that gave better network-based cell clustering than CSN, LIONESS, and CeSpGRN. In unpaired mouse retinal development scRNA-seq and scATAC-seq data, wScReNI had the highest ARI in Seurat-based clustering using gene outdegrees from the top 500 regulatory pairs: CSN 0.488, LIONESS 0.001, CeSpGRN 0.513, kScReNI 0.517, and wScReNI 0.642. ScReNI distinguished RPC1, RPC2, RPC3, and Müller glia cells and provided a procedure for identifying cell-enriched regulators from each cell-specific network.

## Methods used
Nearest-neighbor identification for each target cell; weighted nearest neighbors after multimodal integration; modified random forest modeling of nonlinear regulatory relationships between gene expression and chromatin accessibility; inference of cell-specific regulatory networks; ranking of regulatory pairs; gene outdegree calculation from top-ranked regulatory pairs; Seurat-based and hierarchical clustering; benchmarking against CSN, LIONESS, and CeSpGRN using adjusted Rand index and agreement with reported cell-type labels; evaluation of cell type-specific networks and cell-enriched regulators.

## Method and dataset
ScReNI was evaluated on unpaired mouse retinal development scRNA-seq and scATAC-seq data, focusing on RPC1, RPC2, RPC3, and Müller glia cells; the supplied summary does not report the number of cells. The method is designed for both paired and unpaired scRNA-seq/scATAC-seq datasets. It assumes that nearest-neighbor cells provide informative evidence for a target cell's regulatory network and that regulatory relationships between chromatin accessibility and gene expression can be modeled as nonlinear associations with a modified random forest.

## Limitations
ScReNI depends on accurate scRNA-seq/scATAC-seq integration and reliable nearest-neighbor identification. Performance can be affected by batch effects, sparsity, and imbalance between RNA and ATAC modalities. Some evaluations used representative subsets of cells and selected top regulatory pairs, which may affect scalability and generalizability. Benchmarking partly used available cell annotations and ChIP-seq-derived regulatory relationships as references, which may be incomplete or context-specific. The supplied summary does not report direct comparisons to SCENIC+, FigR, chromVAR, or a detailed scalability assessment on very large datasets.

## Evidence pattern
The paper supported its claims through entity definition of ScReNI as a cell-specific GRN inference method, comparison design against CSN, LIONESS, and CeSpGRN, cell as the statistical unit for cell-specific networks, adjusted Rand index as a clustering performance metric, validation against reported cell-type labels and ChIP-seq-derived regulatory relationships, and boundary-condition discussion for paired/unpaired scRNA-seq and scATAC-seq data.

## Extends or contradicts
ScReNI extends existing cell-specific network inference approaches such as CSN, LIONESS, and CeSpGRN by incorporating both gene expression and chromatin accessibility and by supporting paired and unpaired scRNA-seq/scATAC-seq datasets. It does not directly contradict a prior wiki-listed paper in the supplied summary.

## Boundary conditions
Works when: Works when scRNA-seq and scATAC-seq data can be integrated sufficiently to identify reliable nearest neighbors for each target cell; when neighboring cells are biologically informative for the target cell's regulatory network; and when chromatin accessibility and gene expression contain enough signal to model nonlinear regulator-target relationships. The method applies to both paired and unpaired scRNA-seq/scATAC-seq datasets.
Fails when: May fail or degrade when batch effects distort cross-modality integration, when RNA or ATAC matrices are too sparse to identify reliable neighbors, when one modality dominates or is substantially lower quality, when nearest neighbors do not reflect shared regulatory state, or when reference annotations or ChIP-seq-derived regulatory standards are incomplete or context-inappropriate.
