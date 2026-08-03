---
paper_id: attention_based_cres_2025
title: "An Attention-Based Deep Neural Network Model to Detect Cis-Regulatory Elements at the Single-Cell Level From Multi-Omics Data."
doi: "10.1111/gtc.70000"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC11794194/"
source_ids: {doc_id: "pmc:11794194", pmid: "39904740", pmcid: "11794194", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_peak_to_gene", "multiomic_integration", "multi_grn_inference"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["What PBMC biological validation patterns were used in GLUE or similar RNA+ATAC co-embedding papers?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
Presents an attention-based deep neural network that integrates DNA sequence, genomic distance, and single-cell multi-omics (ATAC + RNA) to detect cis-regulatory elements (cREs) and predict peak–gene links at single-cell resolution. On PBMC single-cell multi-omics it produced higher AUROC for ATAC-peak–gene link detection versus Cicero, ArchR, DIRECT-NET, and Scenic+, improved cell clustering based on predicted cRE activities, and identified tumor-specific SOX2 activity and heterogeneous ZEB1 activation in glioma samples.

## Hypothesis framed
An attention-based deep neural network integrating DNA sequence, genomic distance, and single-cell ATAC+RNA data can detect cREs and predict peak–gene links at single-cell resolution more accurately than existing methods that use rule-based distance priors or population-averaged signals.

## Questions answered
- Does an attention-based DNN that uses DNA sequence, genomic distance, and single-cell ATAC+RNA detect cREs and ATAC-peak–gene links more accurately (AUROC) than Cicero, ArchR, DIRECT-NET, and Scenic+ on PBMC multi-omics data?
- Can single-cell predicted cRE activity from this model improve cell-state clustering and reveal tumor-specific transcription factor activity (e.g., SOX2, heterogeneous ZEB1) in glioma samples?

## Key findings
The model achieved higher AUROC for ATAC-peak–gene link detection on PBMC multi-omics data compared to Cicero, ArchR, DIRECT-NET, and Scenic+ (AUROC reported as the primary metric; numeric values not provided in the summary). Clustering cells using predicted single-cell cRE activities yielded more precise cell-state separation than prior approaches. In glioma datasets the model detected tumor-specific SOX2 activity and heterogeneous activation of ZEB1 across tumor cells that conventional methods reportedly missed. The model learned distance-dependent regulatory patterns from data rather than relying on manual distance priors. Benchmarking used overlaps to FANTOM5 enhancer annotations and promoter-capture Hi-C (PCHiC) links (lifted to hg38) as reference.

## Methods used
Attention-based deep neural network integrating DNA sequence, chromatin accessibility (ATAC peaks), and genomic distance to TSS; training and evaluation on single-cell multi-omics (PBMCs, glioma). Benchmarking versus Cicero, ArchR, DIRECT-NET, and Scenic+ by converting outputs into overlapping ATAC-peak–gene pairs; performance measured using AUROC (sklearn roc_auc_score). Validation references: FANTOM5 enhancers and promoter-capture Hi-C (PCHiC) links (lifted to hg38). Cell clustering evaluated using predicted single-cell cRE activities.

## Method and dataset
Method: attention-based DNN that takes DNA sequence, per-peak chromatin accessibility (single-cell ATAC peaks), and genomic distance to predict cREs and peak–gene links per cell. Data: paired single-cell multi-omics (ATAC + RNA) from healthy human PBMCs and publicly available glioma single-cell multi-omics datasets. Approximate sample sizes, per-cell counts, and replicate numbers are not reported in the provided summary. Assumptions: availability of per-cell ATAC peaks and matched RNA (or multiome) data, reference enhancer annotations (FANTOM5) and PCHiC links for benchmarking, and an hg38 genome coordinate frame for lifted PCHiC.

## Limitations
Benchmarking relied on overlap to curated FANTOM5 enhancers and PCHiC-derived links which may not capture cell-type-specific or functional cREs. PCHiC mapping required liftOver to hg38 and may introduce mapping artifacts. Converting other tools' outputs into overlapping ATAC-peak–gene pairs could bias comparisons because of differing output formats and assumptions. Study tested only PBMC and available glioma datasets—generalizability to other tissues and conditions is unproven. No orthogonal experimental validation (e.g., reporter assays or CRISPR perturbations) of predicted single-cell cRE activity reported. Details on sample/replicate counts, covariates, batch-effect handling, and sensitivity analyses were not provided.

## Evidence pattern
entity_definition, comparison_design, statistical_unit, effect_metric, validation, boundary_conditions; specifically: defined cREs and ATAC-peak–gene pairs, compared model vs Cicero/ArchR/DIRECT-NET/Scenic+ using overlap-based conversion, used single-cell as the statistical unit, reported AUROC (sklearn roc_auc_score) as primary metric, validated against FANTOM5 enhancers and promoter-capture Hi-C (PCHiC) links (lifted to hg38), and discussed dataset- and annotation-related boundary conditions.

## Extends or contradicts
Extends prior peak–gene linking and cRE detection approaches (e.g., Cicero, ArchR) by demonstrating higher AUROC on PBMC multi-omics and by incorporating DNA sequence plus attention to learn distance-dependent regulatory patterns. Contradicts reliance on manually imposed distance priors by showing a data-driven distance learning approach.

## Boundary conditions
Works when: Paired single-cell multi-omics data are available with per-cell ATAC peaks and matched RNA (multiome or equivalent); reference enhancer sets (e.g., FANTOM5) and promoter-capture Hi-C links are available for benchmarking; genome coordinates are in or can be lifted to hg38; input ATAC peak calls and DNA sequence context are of moderate-to-high quality; datasets are similar to the tested PBMC and glioma samples.
Fails when: No paired ATAC+RNA single-cell data are available or ATAC peak calls are low quality; benchmarking references (FANTOM5, PCHiC) are not available or unsuitable for the tissue, causing validation failure; PCHiC liftOver introduces mapping errors; applied to tissues or experimental conditions very different from PBMCs/glioma without additional validation; small cell counts or severe batch effects not addressed by the method may reduce performance.
