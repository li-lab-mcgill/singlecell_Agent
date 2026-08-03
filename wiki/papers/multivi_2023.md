---
paper_id: multivi_2023
title: "MultiVI: deep generative model for the integration of multimodal data."
doi: "10.1038/s41592-023-01909-9"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC10406609/"
source_ids: {doc_id: "pmc:10406609", pmid: "37386189", pmcid: "10406609", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "multi_batch_correction", "atac_batch_correction"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["What data and preprocessing requirements does scvi-tools MultiVI impose for joint RNA+ATAC embedding (e.g., raw counts, peak-by-cell matrix, library size), and how does it handle depth/batch effects?"]
extends: ["peakvi_2022", "hao_2021"]
added: 2026-05-15
session: unknown
---

## Summary
MultiVI is a probabilistic deep generative model implemented in scvi-tools that composes scVI/peakVI/totalVI components to produce a shared latent representation across modalities (RNA, ATAC, protein). It integrates paired and unpaired single-cell multimodal data, explicitly models batch/technical covariates, and can impute missing modalities using information learned from jointly profiled cells.

## Hypothesis framed
A single probabilistic deep generative model that composes modality-specific VAEs (scVI/peakVI/totalVI) can produce a joint latent embedding that (i) integrates heterogeneous modalities, (ii) is robust to missing modalities for some cells, and (iii) accounts for batch/technical effects to enable cross-modality imputation and integrated analysis.

## Questions answered
- Can a unified VAE-based model produce a joint latent embedding for RNA, ATAC and protein data that integrates paired and unpaired cells while correcting batch effects?
- Can such a model impute missing modalities for cells by leveraging jointly profiled multiomic training data?

## Key findings
MultiVI produces a shared latent embedding that coalesces information across modalities and enables integrated downstream analyses even when some cells lack one or more modalities; it can impute missing modality measurements by leveraging paired multiomic cells. The model explicitly models batch/technical covariates via an input S and modality-specific encoders/decoders, enabling application across vertical, horizontal and mosaic integration scenarios.

## Methods used
Variational autoencoder (VAE) framework composing scVI/peakVI/totalVI likelihoods; modality-specific encoder neural networks producing batch-conditioned multivariate normal variational distributions q(z_mod|X_mod,S); penalty term minimizing distance between modality-specific latent representations; integrated latent formed by averaging modality encodings (or using available encoding for unpaired cells); modality-appropriate decoders (count likelihoods for RNA/protein, binary/accessibility likelihoods for ATAC); trained with variational inference/ELBO optimization.

## Method and dataset
Method: MultiVI (composed VAE using scVI/peakVI/totalVI components). Data types: single-cell transcriptome (gene counts), chromatin accessibility (region/peak-by-cell), and protein counts/measurements; supports paired multimodal datasets and datasets with missing modalities (mosaic). Approximate sizes and exact datasets not specified in the summary. Assumptions: Gaussian priors in latent space, modality-appropriate observation likelihoods (count or binary), availability of modality-specific count/accessibility matrices and batch/sample annotations.

## Limitations
Requires sufficient multiomic (paired) training data to learn cross-modality relationships and avoid biased imputations; averaging modality latent representations can oversmooth modality-specific signals; model assumptions (Gaussian latent priors, chosen observation likelihoods) may not fit all datasets; computational cost and hyperparameter tuning can be substantial for very large datasets; performance depends on quality of preprocessed features (peaks, gene sets) and completeness/correct encoding of batch/technical covariates.

## Evidence pattern
entity_definition, controls_covariates, statistical_unit, boundary_conditions

## Extends or contradicts
Extends prior VAE-based single-modality models (scVI, peakVI, totalVI) by composing their encoders/decoders into a joint multimodal model; builds on approaches for integrated multimodal analysis (e.g., Hao et al. 2021) and PeakVI (2022).

## Boundary conditions
Works when: Input consists of modality-specific count/accessibility matrices (genes, chromatin regions/peaks, proteins) with batch/sample annotations S; there is at least some multimodal (paired) data to learn cross-modality relationships; data preprocessing yields feature sets (peaks/genes/proteins) compatible with modality-specific likelihoods; applicable in vertical (shared cells), horizontal (shared features) and mosaic (partial overlap) integration scenarios.
Fails when: Insufficient multimodal (paired) training data to learn cross-modality mappings leading to biased or poor imputations; poor or inappropriate preprocessing/feature selection (e.g., bad peak calling or inappropriate peak selection); violation of model assumptions (e.g., data not well-modeled by chosen count/binary likelihoods or Gaussian latent prior); extremely large datasets where computational resources/hyperparameter tuning are limiting; situations where averaging modality latents masks important modality-specific signals.
