---
paper_id: graph_linked_unified_embedding_2022
title: "Multi-omics single-cell data integration and regulatory inference with graph-linked embedding."
doi: "10.1038/s41587-022-01284-4"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9546775/"
source_ids: {doc_id: "pmc:9546775", pmid: "35501393", pmcid: "9546775", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "multi_grn_inference", "atac_peak_to_gene"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Get the original GLUE method description: how the guidance graph links peaks and genes, the joint embedding learning objective, validation datasets (paired/unpaired RNA+ATAC), and tasks (label transfer, alignment, regulatory inference)."]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
GLUE is a modular computational framework that integrates heterogeneous single-cell omics by combining modality-specific variational autoencoders with a guidance graph encoding prior regulatory links and a graph encoder that links feature embeddings to a shared cell latent space; adversarial alignment aligns modalities. It enables integration of unpaired and triple-omics data, posterior-like regulatory inference (peak-gene links) for unpaired data, and scalable construction of a multi-omics human cell atlas across millions of cells.

## Hypothesis framed
Explicitly modeling cross-omics regulatory interactions via a guidance graph and learning linked feature and cell embeddings will produce more accurate, robust, and scalable integration and enable regulatory inference from unpaired single-cell multi-omics data compared with existing methods.

## Questions answered
- Does GLUE provide more accurate and robust integration of unpaired and paired single-cell RNA and ATAC data compared with state-of-the-art methods?
- Can GLUE infer regulatory peak-to-gene links from unpaired multi-omics data using a prior guidance graph?
- Can GLUE scale to very large datasets (millions of cells) and be used to construct a multi-omics human cell atlas?

## Key findings
GLUE outperformed competing tools across systematic benchmarks on heterogeneous single-cell multi-omics data (paired, unpaired RNA+ATAC and triple-omics) in terms of integration accuracy and robustness; it produced posterior-like regulatory inference linking peaks to genes for unpaired data; it scaled to multi-million-cell integration for a multi-omics human cell atlas and corrected previous cell-type annotations. Specific numerical metrics and per-dataset scores are provided in the paper/supplementary materials.

## Methods used
Modular framework combining omics-specific variational autoencoders with modality-appropriate generative likelihoods; a guidance graph encoding prior regulatory links between features; a graph encoder producing feature embeddings that connect modality decoders to a shared latent cell space; adversarial alignment of cell embeddings across modalities; systematic benchmarking against state-of-the-art integration tools on paired/unpaired and triple-omics datasets.

## Method and dataset
Method: GLUE (graph-linked unified embedding) applied to single-cell RNA-seq, single-cell ATAC-seq, and triple-omics datasets (combinations of RNA, ATAC, and additional modalities). Dataset scale: demonstrated on datasets including up to millions of cells for a multi-omics human cell atlas. Experimental design: integration of unpaired and paired datasets, label transfer, alignment, and regulatory inference benchmarks. Assumptions: availability of a prior guidance graph linking features across modalities (e.g., candidate peak-gene links), that modality-specific probabilistic generative models are appropriate for each data type, and that shared low-dimensional latent structure exists across modalities.

## Limitations
Performance depends on availability and quality of prior regulatory knowledge (guidance graph); incomplete or incorrect priors can limit integration and regulatory inference. Inferred regulatory links require orthogonal experimental validation. Results can be sensitive to hyperparameters and the choice of probabilistic models per modality. Residual modality-specific biases or unmodeled assay effects may remain.

## Evidence pattern
['entity_definition', 'validation', 'comparison_design', 'statistical_unit', 'boundary_conditions']

## Extends or contradicts
Extends prior multimodal integration approaches by explicitly encoding cross-omics regulatory relationships via a guidance graph and learning linked feature/cell embeddings; builds on ideas in generative-model-based integration tools (e.g., MultiVI, Cobolt) but adds explicit regulatory-graph coupling and adversarial alignment.

## Boundary conditions
Works when: Works when a candidate regulatory guidance graph linking features (e.g., peaks to genes) is available and reasonably accurate; applicable to unpaired and paired single-cell RNA, ATAC, and triple-omics datasets; demonstrated to scale to datasets containing up to millions of cells; works when modality-specific likelihoods can be specified and shared latent structure exists across modalities.
Fails when: Fails or degrades when the guidance graph is highly incomplete or contains many incorrect links; when datasets are extremely low cell-count or extremely sparse without appropriate likelihoods; when strong unmodeled assay-specific effects dominate biological signal; performance is sensitive to poor hyperparameter choices or mismatched probabilistic models for modalities.
