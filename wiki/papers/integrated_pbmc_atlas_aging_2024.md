---
paper_id: integrated_pbmc_atlas_aging_2024
title: "An integrated single-cell atlas of blood immune cells in aging."
doi: "10.1038/s41514-024-00185-x"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC11606963/"
source_ids: {doc_id: "pmc:11606963", pmid: "39613786", pmcid: "", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multi_batch_correction", "multi_cell_type_annotation", "rna_differential_expression"]
retrieval_goals: ["prior_findings"]
retrieval_intents: ["Find a PBMC atlas or review listing canonical marker genes per major immune cell type and subsets."]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
The authors integrated seven published 10x Genomics PBMC scRNA-seq datasets (>1 million cells from 103 healthy donors) using consistent marker-based annotation to produce a unified PBMC atlas for young (<40) and old (>60) adults. The atlas reveals consistent age-related trends across cohorts (decline of CD8+ naive and MAIT cells, expansion of non-classical monocytes) and identifies a high-confidence pro-inflammatory aging signature in CD8+ naive T cells.

## Hypothesis framed
Standardizing cell-type annotation across multiple published PBMC single-cell RNA-seq datasets will enable identification of consistent, high-confidence cellular and transcriptional changes associated with human aging.

## Questions answered
- Which PBMC cell types show consistent changes in abundance with aging across multiple published cohorts?
- What are high-confidence, cross-cohort gene-expression signatures of aging in CD8+ naive T cells?
- Is the previously reported MALAT1-high T cell population homogeneous or heterogeneous across datasets?

## Key findings
Integrated >1,000,000 PBMCs from 103 donors (53 young <40, 50 old >60). Consistent cross-cohort decline in CD8+ naive T cells and MAIT cells with age; consistent expansion of non-classical monocyte compartments in older donors. Many other cell types showed substantial inter-study variability. The MALAT1-high T cell population is heterogeneous, containing both naive-like and memory-like cells and varying in abundance across datasets. Despite dataset-specific differential-expression variability, identified a high-confidence aging signature in CD8+ naive T cells characterized by increased expression of pro-inflammatory genes.

## Methods used
Collected seven published 10x Genomics PBMC scRNA-seq studies (3' and 5' chemistries); where needed re-aligned reads with CellRanger to GRCh38; analyzed data in Scanpy; per-sample QC using UMI counts and percent mitochondrial reads with manual thresholds; filtered likely non-PBMC contaminants (high CMTM5, ITGA2B, HBA1, PF4 and low PTPRC); harmonized age groups (young <40, old >60); applied a consistent marker gene set for immune cell annotation; performed integrated analyses of cell-type prevalence and differential gene expression between age groups to derive cross-cohort signatures.

## Method and dataset
Method: marker-driven, cross-dataset integration and comparative scRNA-seq analysis using CellRanger and Scanpy. Data: seven published 10x Genomics PBMC scRNA-seq datasets (mix of 3' and 5' chemistries), totaling >1M cells from 103 healthy adult donors (53 young (<40), 50 old (>60)). Experimental design: retrospective integration of pre-existing datasets, per-sample QC and manual thresholding, unified annotation via a consistent marker gene set, cross-cohort differential expression and abundance analyses. Assumptions: input data are circulating PBMCs from healthy adults, raw or processed matrices are available for reprocessing, marker gene expression is comparable across 3' and 5' chemistries after harmonization, and manual QC thresholds can reliably remove contaminants.

## Limitations
Substantial inter-dataset variability and technical heterogeneity (3' vs 5' chemistries, differing sample prep and pipelines) limit uniformity despite harmonization. Manual per-sample QC thresholds introduce subjectivity. Age-group cutoffs (<40 and >60) and uneven donor sex representation may bias results. Analysis restricted to circulating PBMCs from healthy adults and pre-existing datasets, excluding tissue-resident cells and disease states. Dataset-dependent enrichment affects some findings (e.g., MALAT1-hi heterogeneity) and prospective validation is required.

## Evidence pattern
entity_definition, comparison_design, statistical_unit, effect_metric, validation, boundary_conditions

## Extends or contradicts
Extends prior single-cell studies of immune aging by harmonizing heterogeneous PBMC scRNA-seq datasets with a standardized marker-based annotation to enable cross-cohort comparison and identify high-confidence aging signatures; does not directly contradict prior reports but highlights inter-study variability and dataset-dependent findings.

## Boundary conditions
Works when: Works when datasets are circulating PBMCs from healthy adult donors with age metadata (young <40, old >60), raw or processed matrices are available for reprocessing, data generated on 10x Genomics 3' or 5' chemistries, cohort sizes similar to or larger than ~100 donors and >1M cells where cross-cohort signals can be detected, and when manual QC plus marker-based filtering can remove non-PBMC contaminants.
Fails when: Fails when applied to tissue-resident immune cells or diseased cohorts, pediatric or middle-aged-only cohorts (donors predominantly 40-60), non-10x protocols or platforms with incompatible biases, datasets lacking raw/processed matrices or sufficient metadata, when batch effects are too severe to harmonize across chemistries/protocols, or when marker gene expression is inconsistent across datasets preventing unified annotation.
