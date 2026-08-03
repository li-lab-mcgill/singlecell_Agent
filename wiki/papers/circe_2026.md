---
paper_id: circe_2026
title: "CIRCE: a scalable Python package to predict cis-regulatory DNA interactions from single-cell chromatin accessibility data."
doi: "10.1093/bioinformatics/btag092"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12987762/"
source_ids: {doc_id: "pmc:12987762", pmid: "41734268", pmcid: "12987762", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_peak_to_gene"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Determine which computational method classes are used to integrate paired snRNA-seq and snATAC-seq and infer peak-to-gene or cis-regulatory links from the same cells, and what assumptions they make."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
CIRCE is a scalable Python reimplementation of the Cicero co-accessibility workflow for predicting cis-regulatory DNA interactions from single-cell chromatin accessibility data. The paper shows that CIRCE produces predictions nearly identical to Cicero while reducing runtime and memory by several orders of magnitude, enabling analysis of single-cell chromatin atlases with hundreds of thousands of cells.

## Hypothesis framed
An optimized Python implementation of the Cicero co-accessibility workflow, with optional metacell preprocessing, can preserve cis-regulatory interaction predictions from single-cell chromatin accessibility data while making the method scalable to atlas-scale datasets.

## Questions answered
- Does CIRCE reproduce Cicero co-accessibility-based DNA interaction predictions when run on the same single-cell ATAC-seq input?
- Which preprocessing strategy for single-cell chromatin accessibility matrices best recovers promoter capture Hi-C enhancer-promoter interactions?
- Can a Cicero-derived co-accessibility method process more than 700000 cells and 1 million DNA regions in less than one hour?

## Key findings
CIRCE generated near-identical interaction predictions to Cicero on the same input, with very high correlations between inferred interaction scores. CIRCE reduced runtime and memory usage by several orders of magnitude and processed a dataset with more than 700000 cells and 1 million DNA regions in under one hour. In promoter capture Hi-C benchmarking for PBMCs, the original single-cell count matrix or a binarized count matrix gave the best recovery of reference interactions, Cicero-style count normalization reduced performance, and metacell aggregation did not improve prediction accuracy in the tested settings.

## Methods used
The authors reimplemented the Cicero co-accessibility workflow in Python, added alternative metacell construction strategies, benchmarked CIRCE against Cicero on BMMC and PBMC multiome datasets, compared raw counts, binarized counts, normalized counts, and metacell-based preprocessing, evaluated predicted links against PBMC promoter capture Hi-C enhancer-promoter interactions within 500 kb windows, and tested scalability on an atlas-scale dataset.

## Method and dataset
Method: CIRCE, a Cicero-derived co-accessibility approach for predicting cis-regulatory DNA-region interactions from single-cell chromatin accessibility matrices. Data: BMMC dataset with 1771 cells and 110235 peaks, PBMC dataset with 9631 cells and 215676 peaks, and a scalability dataset with more than 700000 cells and 1 million DNA regions. Experimental design: compare CIRCE and Cicero predictions on matched inputs, test preprocessing choices, validate overlap with promoter capture Hi-C links, and measure runtime and memory. Assumption: genomic regions with correlated accessibility across single cells or metacells, usually within a local genomic window, are candidate cis-regulatory interactions; the method infers putative links rather than directly measuring 3D physical contacts or using RNA-expression correlation.

## Limitations
Biological accuracy was mainly evaluated using promoter capture Hi-C data in PBMCs, so performance across tissues, cell types, platforms, and other reference interaction datasets remains uncertain. CIRCE inherits co-accessibility assumptions and predicts putative regulatory interactions rather than direct chromatin contacts. Metacell aggregation reduced sparsity but did not improve benchmark accuracy in the tested datasets. Small differences from Cicero may arise from stochastic parameter-estimation steps. The study does not evaluate RNA-expression-informed peak-to-gene linkage or integration of paired snRNA-seq and snATAC-seq from the same cells.

## Evidence pattern
Entity definition: CIRCE is defined as a scalable Python implementation of a Cicero-style co-accessibility workflow. Comparison design: CIRCE was compared with Cicero on BMMC and PBMC multiome datasets using matched chromatin accessibility inputs. Effect metrics: concordance of inferred interaction scores, runtime, memory usage, and recovery of promoter capture Hi-C interactions. Validation: inferred DNA-region links were evaluated by overlap with PBMC promoter capture Hi-C enhancer-promoter interactions within 500 kb windows. Boundary conditions: preprocessing choices were varied across raw single-cell counts, binarized counts, normalized counts, and metacells; scalability was tested on more than 700000 cells and 1 million regions.

## Extends or contradicts
Extends the Cicero co-accessibility method class by providing a scalable Python/scverse-compatible implementation and new metacell options. It contradicts the expectation that Cicero-style count normalization or metacell aggregation necessarily improves cis-regulatory interaction recovery, finding that raw or binarized single-cell count matrices performed best in the tested promoter capture Hi-C benchmark.

## Boundary conditions
Works when: Works for single-cell chromatin accessibility or single-cell ATAC-seq count matrices where cis-regulatory links are inferred from co-accessibility across cells or metacells. Demonstrated on datasets ranging from 1771 cells and 110235 peaks to more than 700000 cells and 1 million regions. Best benchmark performance in the reported PBMC promoter capture Hi-C evaluation occurred with raw single-cell counts or binarized counts rather than Cicero-style normalized counts.
Fails when: Does not directly integrate paired snRNA-seq and snATAC-seq, does not use RNA expression to infer peak-to-gene links, and does not directly measure physical chromatin contacts. Cicero-style count normalization reduced promoter capture Hi-C recovery in the reported benchmarks, and metacell aggregation did not improve interaction prediction accuracy. Generalizability is not established for non-PBMC tissues, different platforms, or reference datasets beyond the promoter capture Hi-C benchmark described.
