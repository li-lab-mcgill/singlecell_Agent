---
paper_id: single_nucleus_multi_omics_2025
title: "Single-nucleus multi-omics identifies shared and distinct pathways in Pick's and Alzheimer's disease."
doi: "10.1126/sciadv.ads7973"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12609060/"
source_ids: {doc_id: "pmc:12609060", pmid: "41223260", pmcid: "12609060", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "atac_peak_to_gene", "atac_grn_inference"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Find computational strategies for connecting noncoding AD GWAS risk variants to cell-type-specific scATAC peaks, genes, and regulatory programs."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This paper generated single-nucleus ATAC-seq and RNA-seq maps of postmortem frontal cortex in Pick's disease and controls, then compared them with previously generated Alzheimer's disease single-nucleus datasets. It integrates disease-enriched accessible chromatin, enhancer-gene links, predicted transcription factor occupancy, regulatory networks, and AD GWAS fine mapping to identify shared and disease-specific regulatory programs in neurons and glia.

## Hypothesis framed
Cell type-specific chromatin accessibility and transcriptomic changes in Pick's disease reveal regulatory elements, enhancer-linked genes, and transcription factor programs that are partly shared with Alzheimer's disease but also include disease-specific tauopathy mechanisms.

## Questions answered
- Which cell type-specific chromatin accessibility and gene regulatory programs in Pick's disease are shared with or distinct from Alzheimer's disease?
- Do fine-mapped Alzheimer's disease risk loci overlap disease-relevant single-nucleus ATAC-seq enhancers in specific brain cell types such as microglia?
- Can a predicted distal enhancer associated with UBE3A be functionally validated as a regulatory element by CRISPR excision?

## Key findings
The study found disease-enriched noncoding regions and altered predicted transcription factor binding across neurons and glial cells in Pick's disease and Alzheimer's disease. PiD and AD had overlapping but nonidentical transcription factor regulatory networks in excitatory neurons, astrocytes, microglia, and oligodendrocytes. Fine mapping of AD risk loci showed enrichment in microglial enhancers, with some risk-associated accessible regions also accessible in other cell types. A distal human-gained enhancer associated with UBE3A was identified, and CRISPR excision supported a regulatory role for a predicted UBE3A enhancer.

## Methods used
Single-nucleus ATAC-seq, single-nucleus RNA-seq, major brain cell type annotation, comparison with prior AD single-nucleus ATAC/RNA datasets, disease-enriched chromatin accessibility analysis, promoter-enhancer linking, predicted transcription factor binding and regulatory network inference, AD GWAS fine mapping, immunostaining validation, CRISPR excision of a predicted UBE3A enhancer, and construction of the scROAD database for visualizing predicted single-cell TF occupancy and regulatory networks.

## Method and dataset
The study analyzed postmortem frontal cortex single-nucleus ATAC-seq from 7 Pick's disease and 9 control brains and single-nucleus RNA-seq from 5 Pick's disease and 3 control brains, then compared these data with previously generated Alzheimer's disease single-nucleus ATAC-seq and RNA-seq datasets. Major cell types included excitatory neurons, inhibitory neurons, astrocytes, microglia, oligodendrocytes, oligodendrocyte progenitor cells, and vascular/pericyte-endothelial populations. The regulatory analyses assume that cell type-resolved chromatin accessibility, promoter-enhancer links, TF binding predictions, and fine-mapped GWAS loci can be integrated to nominate disease-relevant enhancers, target genes, and regulatory programs.

## Limitations
The Pick's disease sample size was modest, especially for single-nucleus RNA-seq with 5 PiD and 3 control brains. The use of postmortem frontal cortex may capture late-stage disease, agonal effects, treatment history, postmortem artifacts, or other noncausal changes. Comparisons with Alzheimer's disease used previously generated datasets, which may introduce batch, platform, cohort, or disease-stage confounding. Most enhancer-gene links, transcription factor interactions, and disease-associated regulatory mechanisms remain correlative and were not systematically functionally validated.

## Evidence pattern
The evidence combines entity definition of cell types and regulatory elements, disease-versus-control comparison in PiD, cross-disease comparison with AD, integration of chromatin accessibility with gene expression and promoter-enhancer links, TF occupancy/regulatory network prediction, AD GWAS fine mapping to accessible enhancers, and targeted validation by immunostaining and CRISPR excision of a predicted UBE3A enhancer. Boundary conditions include postmortem human frontal cortex and major annotated brain cell types.

## Extends or contradicts
This extends prior single-nucleus Alzheimer's disease regulatory analyses by adding a Pick's disease frontal cortex multi-omic dataset and directly comparing PiD and AD enhancer and transcription factor regulatory programs. No direct contradiction of a named prior wiki paper is specified in the summary.

## Boundary conditions
Works when: Applies to postmortem human frontal cortex single-nucleus ATAC-seq and RNA-seq datasets with identifiable major brain cell types and enough disease/control donors to compare chromatin accessibility, expression, enhancer-gene links, TF occupancy predictions, and GWAS-enriched regulatory elements. Particularly relevant for analyses prioritizing noncoding AD risk loci in cell type-specific enhancers, including microglial enhancers.
Fails when: The approach is less reliable when donor numbers are too small for disease-versus-control inference, when AD and PiD datasets have unmodeled batch/platform/cohort differences, when disease stage or postmortem variables dominate molecular variation, or when predicted TF binding and enhancer-gene links are interpreted without functional validation.
