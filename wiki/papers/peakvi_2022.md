---
paper_id: peakvi_2022
title: "PeakVI: A deep generative model for single-cell chromatin accessibility analysis."
doi: "10.1016/j.crmeth.2022.100182"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9017241/"
source_ids: {doc_id: "pmc:9017241", pmid: "35475224", pmcid: "9017241", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_batch_correction", "atac_clustering", "atac_differential_accessibility"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["What is the recommended preprocessing for scATAC-seq to mitigate depth bias for joint embedding (TF-IDF followed by LSI), and what failure modes or assumptions are known?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
PeakVI is a deep generative (variational) model for scATAC-seq that models binary detection (presence/absence) using a Bernoulli likelihood decomposed into a learned cell-by-region accessibility probability and explicit region- and cell-specific scaling factors, producing a probabilistic latent embedding that corrects batch and library-size effects and enables single-region differential accessibility testing. The method is implemented in scvi-tools, is benchmarked against existing tools (cisTopic, chromVAR, LSA/LSI, SCALE), and is reported to be scalable, stable, and robust to low-quality data while outperforming these methods on multiple tasks.

## Hypothesis framed
A deep generative model that explicitly models region-specific and cell-specific technical biases and fits a probabilistic latent space from binary detection events will better remove technical and batch effects, preserve biological heterogeneity, and improve differential accessibility and downstream analyses compared with existing scATAC-seq workflows that rely on TF-IDF+LSI or other normalization approaches.

## Questions answered
- Does explicitly modeling region- and cell-level technical factors with a variational deep generative model produce latent embeddings that remove batch/library-size effects while preserving biological heterogeneity?
- Does PeakVI improve single-region differential accessibility detection and downstream clustering/annotation relative to methods such as cisTopic, chromVAR, LSA/LSI, and SCALE?
- Is PeakVI scalable and robust to low-quality or noisy scATAC-seq datasets and typical batch effects encountered in public datasets?

## Key findings
PeakVI yields a smooth probabilistic latent space that preserves biological heterogeneity while removing technical and batch effects; explicit modeling of region-specific (r_j) and cell-specific (ℓ_i) biases improves denoising and interpretability relative to methods that rely on TF-IDF+LSI; PeakVI enables single-region differential accessibility testing useful for cell-type annotation and cis-regulatory element discovery; across multiple public datasets the method is reported to be scalable, stable, robust to low-quality data, and to outperform cisTopic, chromVAR, LSA/LSI, and SCALE on a range of benchmarking tasks. The approach depends on peak/region definitions and uses a Bernoulli observation model (detection only), which limits use of quantitative fragment-count information.

## Methods used
Variational autoencoder-style deep generative model with Bernoulli observation model on detection (x_ij>0); decomposition of detection probability into learned cell-by-region accessibility (via neural network/latent representation) and explicit region-specific (r_j) and cell-specific (ℓ_i) scaling factors; variational inference and neural-network encoders/decoders scaling with input size; UMAP and clustering on latent embeddings; single-region differential accessibility testing using the probabilistic model; benchmarking and comparisons against cisTopic, chromVAR, LSA/LSI, and SCALE; regularization via data holdout, validation monitoring, and early stopping.

## Method and dataset
Method: PeakVI (deep generative variational model) applied to scATAC-seq cell-by-region count matrices converted to detection (binary) input. Data: multiple public scATAC-seq datasets of varying sizes and qualities (exact dataset names and cell counts not specified in the summary); experimental design: benchmarking across tasks (batch correction, clustering, differential accessibility) versus competing methods. Key assumptions: requires an input peak/region definition, treats observed counts as binary detection events (Bernoulli likelihood), assumes region-specific and cell-specific multiplicative technical factors can explain non-biological variation (r_j and ℓ_i), and that biological accessibility can be captured in a low-dimensional latent representation.

## Limitations
Depends on upstream peak/region definitions and inherits biases from peak calling; reduces counts to binary detection events and therefore does not capture quantitative fragment-count information beyond presence/absence; may require substantial computational resources and hyperparameter tuning for very large datasets; performance can be sensitive for extremely low-coverage cells and very rare cell types; potential sensitivity to incorrect assumptions about the sufficiency of region- and cell-wise scaling to capture all technical confounders.

## Evidence pattern
['comparison_design', 'controls_covariates', 'validation', 'boundary_conditions', 'statistical_unit']

## Extends or contradicts
Provides a critique and alternative to TF-IDF+LSI approaches by explicitly modeling cell-specific (library size/depth) and region-specific biases instead of relying on TF-IDF normalization; positions PeakVI as an alternative that can outperform LSI-based pipelines for embeddings and differential testing on the evaluated datasets.

## Boundary conditions
Works when: Input peak/region definitions are provided and reliable; biological signal is predominantly captured by detection (presence/absence) rather than requiring quantitative fragment counts; library-size and region-specific biases are primary technical confounders; datasets include batch effects to be corrected; applied to small-to-large scATAC-seq datasets (authors demonstrate scalability and robustness across multiple public datasets).
Fails when: PeakVI is likely to fail or be less appropriate when peak calling is poor or introduces strong biases, when quantitative fragment-count information (read depth per peak) is critical and cannot be reduced to detection events, for extremely low-coverage cells or extremely rare cell types where the Bernoulli formulation and learned latent factors lack power, when computational resources or hyperparameter tuning are severely limited, or when technical confounders are not well modeled by multiplicative region- and cell-specific scaling.
