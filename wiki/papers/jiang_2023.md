---
paper_id: jiang_2023
title: "Destin2: Integrative and cross-modality analysis of single-cell chromatin accessibility data."
doi: "10.3389/fgene.2023.1089936"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9981783/"
source_ids: {doc_id: "pmc:9981783", pmid: "36873935", pmcid: "9981783", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "atac_clustering", "atac_cell_type_annotation"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["What evidence supports multimodal variational generative models for paired RNA+ATAC co-embedding and clustering on 10x Multiome-scale data?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
Destin2 is an R-package method that integrates three scATAC-derived modalities—peak accessibility (LSI/LDA), transcription factor motif deviation (chromVAR), and pseudo-gene activity—into a shared low-dimensional manifold for clustering and trajectory inference. Benchmarking on four public scATAC datasets and on matched single-cell multiome pairs shows improved or corroborating clustering and trajectory performance relative to unimodal pipelines and better preservation of true cell–cell similarities.

## Hypothesis framed
Integrating modality-specific scATAC embeddings (peaks, motif deviations, pseudo-gene activity) into a shared manifold produces more accurate clustering and trajectory reconstruction and better preserves true cell–cell similarities than unimodal scATAC analyses.

## Questions answered
- Does integrating peak accessibility, motif-deviation, and pseudo-gene activity embeddings into a shared manifold improve clustering accuracy (ARI/AMI/homogeneity) and separation (cLISI) relative to unimodal scATAC pipelines on 10x and other public scATAC datasets?
- Does cross-modality integration preserve true cell–cell similarities when evaluated using matched single-cell RNA+ATAC (multiome) paired cells as ground truth?

## Key findings
Across four evaluated datasets (10x PBMCs, 10x adult mouse cortex, human BMMCs, human fetal organs) Destin2 produced higher ARI, AMI and homogeneity scores and improved cLISI separation versus unimodal pipelines (Signac, cisTopic, chromVAR, MAESTRO). On matched single-cell multiome pairs, Destin2 better preserved true cell–cell similarities compared to unimodal scATAC analyses. The integration step is computationally lightweight on modest hardware, and ensembling peak preprocessing models increases robustness; however, motif scoring (chromVAR) and some preprocessing steps are runtime/memory bottlenecks.

## Methods used
Modality-specific preprocessing: LSI/LDA for peak accessibility, chromVAR for TF motif deviation scoring, aggregation to pseudo-gene activity; integration by learning a shared low-dimensional manifold from these embeddings; clustering and trajectory inference on the shared manifold; benchmarking with CCA-based label transfer from matched scRNA-seq or curated labels; comparative evaluation against Signac, cisTopic, chromVAR, MAESTRO using ARI, AMI, homogeneity score and cLISI metrics.

## Method and dataset
Method: Destin2 integrates three modality-specific low-dimensional embeddings (peak LSI/LDA, chromVAR motif deviations, pseudo-gene activity) into a shared manifold for clustering and trajectory reconstruction; supports ensembling of peak-preprocessing methods and mini-batching to mitigate computational bottlenecks. Data: applied to four public scATAC datasets (10x PBMCs, 10x adult mouse cortex, human BMMCs, human fetal organs) and to matched single-cell RNA+ATAC multiome pairs for validation. Experimental design: benchmarking vs unimodal scATAC pipelines with ground truth supplied by CCA label transfer from matched scRNA or curated labels. Assumptions: availability of modality-specific preprocessing outputs (peaks, motif scores, gene activity) and reasonably accurate external labels for benchmarking.

## Limitations
Performance depends on the quality of modality-specific preprocessing (peak calling, motif scoring, pseudo-gene aggregation) and on external label-transfer when unmatched scRNA labels are used as ground truth, which can bias evaluation. chromVAR motif scoring and some preprocessing steps are computationally intensive and may not scale to atlas-size datasets without mini-batching or alternative scalable motif methods. Evaluation was limited to four datasets and selected comparator tools; no direct comparisons were run against published multimodal VAE methods (e.g., multiVI, Cobolt, scMM, totalVI/SCVI-based models).

## Evidence pattern
entity_definition, comparison_design, statistical_unit, effect_metric, validation, boundary_conditions

## Extends or contradicts
Extends prior unimodal scATAC analysis pipelines (e.g., Signac, cisTopic, chromVAR, MAESTRO) by demonstrating improved clustering/trajectory metrics via cross-modality integration; does not directly compare to or contradict published multimodal VAE-based co-embedding models.

## Boundary conditions
Works when: Works when input scATAC data can provide three modality-specific embeddings (peak LSI/LDA, chromVAR motif deviation scores, and pseudo-gene activity); modality-specific preprocessing is high quality; datasets are similar in type to those tested (10x PBMCs, 10x adult mouse cortex, human BMMCs, human fetal organs); matched multiome pairs or reliable external labels are available for validation; modest hardware suffices for the integration step (with chromVAR/preprocessing compute available or mitigated by mini-batching).
Fails when: Fails or degrades when modality-specific preprocessing is poor or absent (no reliable peaks, motif scores, or gene activity), when external label-transfer provides inaccurate ground truth, when scaling to atlas-scale datasets without mini-batching or scalable motif methods due to chromVAR/preprocessing memory/runtime bottlenecks, or when direct comparison to multimodal VAE approaches is required (no evidence provided).
