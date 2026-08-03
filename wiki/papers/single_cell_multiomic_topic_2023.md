---
paper_id: single_cell_multiomic_topic_2023
title: "Single-cell multi-omic topic embedding reveals cell-type-specific and COVID-19 severity-related immune signatures."
doi: "10.1101/2023.01.31.526312"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9915637/"
source_ids: {doc_id: "pmc:9915637", pmid: "36778483", pmcid: "9915637", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "multi_batch_correction", "atac_motif_analysis"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["What evidence supports multimodal variational generative models for paired RNA+ATAC co-embedding and clustering on 10x Multiome-scale data?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
This paper introduces moETM, a multimodal variational topic model that integrates paired single-cell modalities (scRNA+scATAC and CITE-seq) using a product-of-experts encoder and a factorized linear decoder to produce interpretable shared topic embeddings. The model is benchmarked against six state-of-the-art integration methods on seven public multi-omic datasets and is used to recover cell-type signatures, transcription-factor motifs in ATAC topics, and COVID-19 severity-associated multi-omic biomarkers.

## Hypothesis framed
A product-of-experts variational encoder combined with a factorized linear decoder (moETM) yields tighter variational posteriors, more robust multimodal co-embeddings, and more interpretable multi-omic topics than existing integration methods, enabling recovery of cell-type-specific signatures and disease-associated biomarkers.

## Questions answered
- Does combining modality-specific latent Gaussians via a product-of-experts encoder improve integration and co-embedding quality for paired scRNA+scATAC and CITE-seq data compared to existing methods?
- Can a factorized linear decoder produce interpretable joint multi-omic topics that recover known cell types and regulatory motifs from scRNA+scATAC data?
- Can moETM identify multi-omic signatures associated with COVID-19 severity from CITE-seq patient data while correcting batch effects across studies?

## Key findings
moETM outperformed six competing single-cell integration methods across seven public multi-omic datasets (scRNA+scATAC and CITE-seq) in integrative analyses (quantitative metrics not provided in the summary). The factorized linear decoder yielded interpretable multi-omic topics that mapped to known cell types and marker features. On human bone marrow mononuclear cells (BMMCs) moETM topics recovered sequence motifs corresponding to transcription factors regulating immune gene signatures. On COVID-19 CITE-seq data moETM identified established immune cell-type-specific signatures and composite multi-omic biomarkers associated with critical disease; batch effects across studies were corrected by a linear intercept term.

## Methods used
Variational autoencoder/topic model (moETM) with modality-specific encoders producing latent Gaussians combined via product-of-experts (product-of-Gaussians) to form a joint posterior; logistic-normal topic proportions; factorized linear decoder decomposing per-modality topic matrices into topic embedding (α) and modality-specific feature embeddings (ρ^(m)); linear intercept for batch/study correction; benchmarking against six state-of-the-art methods on seven public datasets; downstream analyses including top-topic feature extraction, motif discovery on ATAC-derived topics, and association analysis of topics with COVID-19 severity.

## Method and dataset
moETM applied to paired single-cell modalities: scRNA+scATAC datasets (including human BMMCs) and CITE-seq (protein+RNA) datasets from multiple public studies. Design: per-cell paired multi-omic count matrices across studies with batch/study covariates; no explicit cell counts or exact dataset sizes provided in the summary. Assumptions: topic-modeling formulation (K topics, logistic-normal latent), modality-specific latent Gaussians are approximately Gaussian, additive batch effects correctable by a linear intercept, and linear factorization suffices for interpretable feature-topic mappings.

## Limitations
Linear factorized decoder may not capture complex nonlinear interactions between features and modalities; performance and interpretability depend on hyperparameter choices (number of topics K, embedding size L) and preprocessing of count data; evaluated modalities limited to scRNA, scATAC, and protein (CITE-seq) — behavior on other or noisier modalities untested; no reported scalability/runtime/memory benchmarks for very large 10x Multiome-scale datasets in the summary.

## Evidence pattern
entity_definition, comparison_design, effect_metric, validation, controls_covariates, boundary_conditions, analysis_used

## Extends or contradicts
Extends prior multimodal variational/topic-model approaches and contrasts with mixture-of-experts encoders by using a product-of-experts encoder and a factorized linear decoder to improve variational tightness and interpretability.

## Boundary conditions
Works when: Input are paired single-cell count modalities per cell (scRNA+scATAC or CITE-seq) with counts preprocessed; number of latent topics K and embedding dimensions are chosen appropriately; batch/study effects are approximately additive and can be modeled via a linear intercept; topic-model assumptions (cells as mixtures over latent topics) are valid.
Fails when: When important cross-modality feature relationships are highly nonlinear and cannot be captured by a linear decoder; when batch effects are non-additive or require complex hierarchical correction; when data modalities not evaluated (other modalities or substantially noisier data) are used; or when scaling to very large Multiome datasets requires runtime/memory characteristics not demonstrated in the paper.
