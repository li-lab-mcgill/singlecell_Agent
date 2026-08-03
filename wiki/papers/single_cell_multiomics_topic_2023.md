---
paper_id: single_cell_multiomics_topic_2023
title: "Single-cell multi-omics topic embedding reveals cell-type-specific and COVID-19 severity-related immune signatures."
doi: "10.1016/j.crmeth.2023.100563"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC10475851/"
source_ids: {doc_id: "pmc:10475851", pmid: "37671028", pmcid: "10475851", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "multi_batch_correction", "atac_motif_analysis"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["What evidence supports multimodal variational generative models for paired RNA+ATAC co-embedding and clustering on 10x Multiome-scale data?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
This paper introduces moETM, a VAE-based multimodal integration method that combines per-modality logistic-normal latent distributions via a product-of-Gaussians encoder and uses linear modality-specific decoders with a linear intercept for batch correction. moETM is benchmarked against six state-of-the-art methods on seven public datasets and is reported to produce more robust joint embeddings, interpretable topic loadings, TF motif links from scRNA+scATAC, and multi-omic immune signatures in COVID-19 CITE-seq PBMCs.

## Hypothesis framed
A product-of-Gaussians encoder combined with linear modality-specific decoders and linear batch intercepts will produce more robust, lower-variance joint embeddings and more interpretable multimodal topic factors than existing mixture-of-experts VAE approaches for single-cell multi-omics (including paired scRNA+scATAC and CITE-seq).

## Questions answered
- Does a product-of-Gaussians (PoG) encoder reduce Monte Carlo sampling noise and improve joint embedding robustness compared to mixture-of-experts encoders for paired scRNA+scATAC integration?
- Does moETM outperform six state-of-the-art multimodal integration methods on integration/embedding quality and interpretability across seven public multi-omics datasets?
- Can topics learned from paired scRNA+scATAC data via moETM recover transcription-factor motif associations and can moETM identify cell-type and COVID-19 severity-associated multi-omics signatures in CITE-seq PBMCs?

## Key findings
moETM produced joint per-cell embeddings that the authors report as superior to six comparator methods across seven datasets for integration and embedding quality (no numerical metrics provided in the summary). The PoG encoder reduced sampling noise relative to MoE encoders and the linear decoders produced directly interpretable topic loadings (genes, proteins, peaks). On scRNA+scATAC data moETM-derived topics recovered sequence motifs corresponding to transcription factors regulating immune gene programs. On COVID-19 CITE-seq PBMC data moETM identified known immune cell-type-specific signatures and composite multi-omics biomarkers associated with critical disease states.

## Methods used
Variational autoencoder with per-modality K-dimensional logistic-normal latent distributions combined via a product-of-Gaussians encoder; modality-specific linear decoders producing topic feature loadings; linear intercept terms for batch correction; benchmarking against six competing methods on seven public datasets (CITE-seq, 10x multiome/scRNA+scATAC, SHARE-seq, sci-CAR); motif enrichment/association analysis linking scATAC peaks/topics to TF motifs; downstream interpretation of topics for cell-type and disease-severity signatures.

## Method and dataset
moETM (PoG encoder + linear decoders with linear batch intercept) applied to paired single-cell multimodal data including scRNA+scATAC (multiome and multiome-like datasets), CITE-seq PBMCs from COVID-19 patients, SHARE-seq and sci-CAR datasets; benchmarked across seven public datasets. Experimental design: unsupervised topic-model-style embedding per cell, downstream extraction of top features per topic, motif enrichment for scATAC topics, and interpretation of topics for cell-type and severity associations. Assumptions: modalities have per-modality logistic-normal latent representations; product-of-Gaussians combination yields lower sampling variance; linear decoders suitably capture feature-topic relationships and linear intercepts model batch shifts.

## Limitations
PoG encoder and linear decoders impose specific probabilistic and linear structures that may miss complex nonlinear cross-modality interactions. Benchmarking is limited to seven public datasets and the tested modalities (transcriptome, proteins, chromatin); performance on other modality combinations or much larger cohorts is untested. Biological associations (TF links, COVID-19 biomarkers) require independent experimental validation. Results sensitive to choice of topic number K and preprocessing. Linking sparse scATAC peak-topic signals to target genes can be challenging and ambiguous.

## Evidence pattern
entity_definition, comparison_design, statistical_unit, effect_metric, controls_covariates, validation, boundary_conditions

## Extends or contradicts
Extends prior VAE-based multimodal integration approaches (e.g., TotalVI, MultiVI, scMM) by replacing MoE-style encoder combinations with a product-of-Gaussians encoder to reduce variational sampling noise and by using linear decoders and intercepts to improve interpretability and batch correction.

## Boundary conditions
Works when: Data are paired per cell (e.g., scRNA+scATAC or CITE-seq) with high-dimensional, sparse modalities where batch labels or batch factors are available for linear intercept correction; topic model formulation (choice of K) is appropriate for the biological heterogeneity present; datasets comparable in size and complexity to the seven public datasets used in the paper (multiome/CITE-seq/SHARE-seq/sci-CAR).
Fails when: Modalities involve strong nonlinear cross-modality interactions that cannot be captured by linear decoders; modalities or scales not tested (e.g., spatial modalities, metabolomics) where assumptions may not hold; extremely large cohorts or 10x Multiome-scale datasets where scalability/runtime/memory were not demonstrated; highly misspecified topic number K or incompatible preprocessing; very sparse scATAC data that prevent reliable peak-to-gene linking.
