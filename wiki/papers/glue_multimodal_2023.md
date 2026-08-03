---
paper_id: glue_multimodal_2023
title: "GLUE multimodal single cell data."
doi: "10.1093/pcmedi/pbad007"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC10052360/"
source_ids: {doc_id: "pmc:10052360", pmid: "37007746", pmcid: "10052360", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "multi_grn_inference", "multi_cell_type_annotation"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Get the original GLUE method description: how the guidance graph links peaks and genes, the joint embedding learning objective, validation datasets (paired/unpaired RNA+ATAC), and tasks (label transfer, alignment, regulatory inference)."]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
This commentary summarizes the GLUE framework, which couples modality-specific representations using a guidance graph linking features (peaks, genes, motifs) to learn a joint low-dimensional embedding that preserves cell-level similarity and feature–feature relationships. The authors report that GLUE improves multimodal alignment and annotation transfer relative to prior methods and yields interpretable putative regulatory links recoverable from RNA/ATAC/motif data.

## Hypothesis framed
Coupling modality-specific embeddings via a guidance graph of feature–feature relationships enables improved joint embeddings that both align cells across modalities and recover putative cis-regulatory links at single-cell resolution.

## Questions answered
- Does integrating feature-level guidance (a guidance graph linking peaks, genes, motifs) improve cross-modality alignment and label transfer compared with existing cell-alignment methods?
- Can a joint embedding learned with graph-linked coupling recover known gene–peak or motif–gene associations and suggest novel regulatory candidates?
- Does GLUE perform well on both paired and unpaired RNA+ATAC datasets for tasks including label transfer, clustering, and regulatory inference?

## Key findings
GLUE produces a unified low-dimensional embedding that improves multimodal alignment and downstream tasks (clustering, annotation transfer) relative to prior methods; it recovers many known gene–peak and motif–gene links and proposes additional putative regulatory relationships; the framework is flexible across modalities (scRNA, scATAC, protein/ADTs) and scales to moderate-to-large single-cell datasets.

## Methods used
Guidance graph connecting modality-specific features (peaks↔genes↔motifs), graph-linked unified embedding model that jointly learns modality-specific encoders and a shared low-dimensional embedding, graph-based information transfer across modalities, benchmarking on multiple paired and unpaired RNA+ATAC datasets, evaluation via alignment accuracy, label transfer performance, and recovery of known regulatory links.

## Method and dataset
Method: GLUE (graph-linked unified embedding) applied to multimodal single-cell data (scRNA-seq, scATAC-seq, motifs, ADTs). Data: benchmarking reported on several paired and unpaired RNA+ATAC datasets and other modality combinations (exact dataset names and sizes not provided in the commentary). Experimental design: validation included alignment/label-transfer benchmarks and recovery of known regulatory associations. Assumptions: requires a guidance graph linking features (peaks↔genes/motifs) and assumes sufficient overlap of biological signal across modalities and availability of prior annotations to build the guidance graph.

## Limitations
Performance depends on the quality and completeness of the input guidance graph and prior annotations; inferred regulatory links are putative and require experimental validation; high sparsity, strong technical confounders, or poorly matched modalities can reduce accuracy; outputs and performance are sensitive to parameter choices and graph construction; computational cost may be nontrivial for very large or many-modality datasets.

## Evidence pattern
entity_definition, comparison_design, validation, boundary_conditions

## Extends or contradicts
Extends prior multimodal integration approaches (e.g., methods that align cells across modalities such as MultiVI and other joint-integration tools) by explicitly coupling feature-level links via a guidance graph to enable regulatory inference at the feature level.

## Boundary conditions
Works when: Works when a reasonably complete, biologically meaningful guidance graph is available linking modality-specific features (e.g., peaks to genes or motifs), modalities share underlying biological signal (shared or overlapping cell types), prior annotations exist to construct the guidance graph, and dataset sizes are moderate-to-large (i.e., sufficient cells per modality to learn joint structure).
Fails when: Fails or degrades when the guidance graph is sparse, incorrect, or missing key links; when modalities are extremely sparse or have strong unmatched technical confounders/batch effects; when modalities do not share cell types or biological signal; when parameter choices or graph construction are poor; or when computational resources are insufficient for very large or many-modality datasets.
