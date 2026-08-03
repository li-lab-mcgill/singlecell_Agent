---
paper_id: single_cell_rnaseq_precdcs_2019
title: "Single cell RNA-Seq reveals pre-cDCs fate determined by transcription factor combinatorial dose."
doi: "10.1186/s12860-019-0199-y"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC6599345/"
source_ids: {doc_id: "pmc:6599345", pmid: "31253076", pmcid: "6599345", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_clustering", "rna_differential_expression", "rna_grn_inference"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["Obtain marker definitions for DC subsets cDC1, cDC2, pDC in human PBMC by scRNA and scATAC"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
Using Fluidigm C1 single-cell RNA-Seq and complementary bulk RNA-Seq of FACS-enriched human peripheral blood cDC1 (CD141+), cDC2 (CD1c+) and pre-cDCs, the study identifies 16 transcription factors whose combinatorial expression stratifies pre-cDCs into cDC1-like and cDC2-like subpopulations. The authors report that the ratio of IRF8 to IRF4 expression in single cells correlates with pre-cDC lineage bias, a result validated in three external datasets.

## Hypothesis framed
Combinatorial dosage of transcription factors, particularly the IRF8/IRF4 expression ratio, determines pre-cDC fate bias toward cDC1 versus cDC2 in human peripheral blood.

## Questions answered
- Can human peripheral blood pre-cDC subpopulations be separated into cDC1-like and cDC2-like lineages by transcription factor expression signatures?
- Is the ratio of IRF8 to IRF4 expression in single pre-cDCs a better correlate of lineage bias than the absolute expression of either IRF8 or IRF4 alone?

## Key findings
Single-cell transcriptomes distinguish pre-cDC, cDC1 and cDC2. Pre-cDC heterogeneity is not separable by highly variable genes within pre-cDCs nor by bulk cDC1/cDC2 DE genes alone; instead, a set of 16 transcription factors separates pre-cDCs into two subpopulations aligning with cDC1-like and cDC2-like identities. The IRF8/IRF4 expression ratio in single pre-cDCs correlates with lineage bias more strongly than individual IRF8 or IRF4 expression. Findings were validated in three independent published datasets.

## Methods used
FACS enrichment and sorting of human peripheral blood cDC1 (CD141+), cDC2 (CD1c+) and pre-cDCs; Fluidigm C1 single-cell RNA-Seq across three mixed-cell batches; bulk RNA-Seq of sorted populations; single-cell clustering and differential expression analyses; selection of candidate master regulators by (1) TFs differentially expressed between bulk cDC1 and cDC2 or (2) TFs whose targets are enriched among cDC DE genes; stratification of pre-cDCs by these TFs; cross-validation in three external datasets.

## Method and dataset
Fluidigm C1 scRNA-Seq of FACS-enriched human peripheral blood pre-cDCs, cDC1, and cDC2 (three mixed-cell batches; high-quality single-cell counts on the order of tens per batch) plus bulk RNA-Seq of sorted populations. Assumptions: sorting markers reliably enrich target populations; Fluidigm C1 sensitivity captures TF expression; TF-target relationships can be inferred from target enrichment analyses. Exact donor/sample counts not specified in the summary.

## Limitations
Small numbers of high-quality single cells (tens per batch) and sampling limited to peripheral blood restrict generalizability; analyses are correlative with no perturbation or functional differentiation assays to demonstrate causality; potential batch effects, marker-based sorting biases, and platform sensitivity limits; no single-cell ATAC-seq or chromatin accessibility data and no explicit pDC marker profiling within this study.

## Evidence pattern
entity_definition (defined cDC1, cDC2, pre-cDC by sorting and scRNA profiles); comparison_design (bulk cDC1 vs cDC2 DE genes, pre-cDC stratification by TF sets); statistical_unit (single cells and bulk-sorted samples); metric (differentially expressed genes, TF expression levels and IRF8/IRF4 ratio); covariates considered (batch/mixed-cell batches, sorting enrichment); validation (replication of TF signature and IRF8/IRF4 correlation in three external published datasets); boundary_conditions (human peripheral blood samples, Fluidigm C1 platform).

## Extends or contradicts
Extends prior observations that human pre-cDCs are heterogeneous and include pre-committed subpopulations by identifying a specific set of 16 transcription factors and proposing a combinatorial dose (IRF8/IRF4 ratio) model that correlates with pre-cDC fate bias.

## Boundary conditions
Works when: Applied to FACS-enriched human peripheral blood DCs (pre-cDC, cDC1 CD141+, cDC2 CD1c+); scRNA-Seq data generated on platforms with sensitivity comparable to Fluidigm C1; sample sizes with tens of high-quality single cells per batch and availability of bulk RNA-Seq of sorted populations for DE comparisons; external datasets from human blood available for validation.
Fails when: Datasets from tissues other than peripheral blood, when cell counts per subtype are very low (<~10 high-quality single cells per subtype), when no enrichment/sorting is performed and DCs are rare in the input, when causal inference via perturbation is required (study is correlative), or when using modalities other than scRNA-Seq (e.g., only scATAC-seq) without complementary expression data.
