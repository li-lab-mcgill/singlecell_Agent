---
paper_id: reunion_2024
title: "REUNION: transcription factor binding prediction and regulatory association inference from single-cell multi-omics data."
doi: "10.1093/bioinformatics/btae234"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC11211829/"
source_ids: {doc_id: "pmc:11211829", pmid: "38940155", pmcid: "11211829", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multi_grn_inference", "multiomic_integration", "atac_grn_inference"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["What PBMC biological validation patterns were used in GLUE or similar RNA+ATAC co-embedding papers?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
REUNION is a two-component framework (Unify + Rediscover) that predicts genome-wide TF binding and infers cis-region–TF–gene regulatory triplets from single-cell multi-omics (RNA+ATAC) data without requiring ChIP-seq training. Applied to 10x PBMC multiome data, it recovers TF–region associations including motif-less peaks and improves prediction of target gene expression compared to motif-scanning and footprinting baselines.

## Hypothesis framed
Combining information-theory-based scores that integrate TF expression, chromatin accessibility, and target gene expression with a pseudo semi-supervised learner trained on latent accessibility and sequence features can predict TF binding genome-wide and recover regulatory region–TF–gene triplets from single-cell multi-omics data without ChIP supervision, outperforming motif-scanning and footprinting approaches.

## Questions answered
- Does REUNION outperform representative single-cell GRN/TFBS methods, motif collections, and footprinting (e.g., TOBIAS) for TF binding prediction on PBMC multiome data?
- Can regulatory region–TF associations be recovered in accessible peaks that lack detected TF motifs, and do these recovered associations improve prediction of target gene expression in inferred triplets?
- What PBMC-specific validation design and statistical unit are practical for benchmarking multi-omic TF binding prediction methods?

## Key findings
On 10x PBMC multiome data aggregated into 490 metacells and benchmarked against 67 public ChIP-seq datasets (covering 59 TFs across four cell types), REUNION achieved higher average TF binding prediction performance than competing methods. It recovered region–TF associations in peaks lacking detected motifs and incorporation of these newly identified associations improved prediction of target gene expression within inferred cis-region–TF–gene triplets.

## Methods used
Unify: information theory–inspired complementary score functions combining TF expression, peak accessibility, and target gene expression to prioritize peak–TF–gene links; Rediscover: pseudo semi-supervised learning using latent chromatin-accessibility and sequence feature spaces to predict TF binding in accessible regions (motif-present or motif-less) without ChIP supervision; benchmarking against 67 public ChIP-seq datasets, comparisons to multiple motif collections and footprinting tools (e.g., TOBIAS); aggregation of single-cell profiles into 490 metacells from 10x Genomics PBMC multiome.

## Method and dataset
Method: REUNION (Unify + Rediscover) on paired single-cell RNA+ATAC (10x Genomics multiome) PBMC data aggregated into 490 metacells; Benchmark: 67 public ChIP-seq datasets (59 TFs, 4 cell types). Assumptions: TF expression, peak accessibility, and target expression jointly inform regulatory links; latent accessibility and sequence feature spaces are informative for pseudo-labeled learning; no ChIP-seq supervision required for Rediscover training.

## Limitations
Unify scores individual peak–TF–gene links and does not explicitly model combinatorial interactions among multiple TFs or peaks. Rediscover's performance depends on the chosen feature representations and quality of pseudo-labeled examples, making it sensitive to feature engineering and label noise. Benchmarking and validation were performed on PBMC multiome data with available ChIP sets; generalizability to other tissues or cell types is untested. Lack of supervised ChIP training can produce false positives.

## Evidence pattern
entity definition: peak–TF–gene 'triplet' regulatory associations; comparison design: benchmark REUNION vs representative single-cell GRN/TFBS methods, multiple motif collections, and footprinting (e.g., TOBIAS); statistical unit: 10x PBMC single-cell multiome aggregated into 490 metacells; effect metric: average TF binding prediction performance across 67 public ChIP-seq datasets (59 TFs, 4 cell types) and improvement in target gene expression prediction within triplets; covariates: not specified in summary; validation: benchmarking to 67 ChIP-seq datasets and demonstrating improved gene expression prediction when including recovered region–TF links; boundary conditions: evaluated on PBMC multiome only; analysis used: information-theoretic scoring (Unify) and pseudo semi-supervised learning on latent accessibility and sequence features (Rediscover).

## Extends or contradicts
Extends and circumvents limitations of motif-scanning and footprinting-based TFBS assignment (e.g., TOBIAS and motif-collection approaches) by recovering motif-less region–TF associations and improving gene expression prediction when those associations are included.

## Boundary conditions
Works when: Paired single-cell RNA+ATAC (10x Genomics multiome) data are available and can be aggregated into metacells (example: 490 metacells from PBMC data); TF expression is measured and accessible peaks exist; latent chromatin accessibility and sequence feature representations are informative; benchmarking resources (ChIP-seq datasets) are available for evaluation (e.g., up to 67 ChIP datasets across many TFs).
Fails when: Data from tissues or cell types without available ChIP references for benchmarking; datasets with poor or noisy TF expression measurements; situations where combinatorial TF interactions dominate regulatory logic (Unify does not model combinations); when latent feature representations are uninformative or pseudo-labels are highly noisy; small sample sizes or no metacell aggregation may reduce performance and increase false positives.
