---
paper_id: single_cell_transcriptomic_analysis_2019
title: "Single-cell transcriptomic analysis of Alzheimer's disease."
doi: "10.1038/s41586-019-1195-2"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC6865822/"
source_ids: {doc_id: "pmc:6865822", pmid: "31042697", pmcid: "6865822", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_clustering", "rna_differential_expression", "rna_gene_programs"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["Learn which brain cell populations and disease-associated cellular states are reproducibly implicated in human Alzheimer's disease single-cell/nucleus transcriptomics, and how those states are biologically defined and validated."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study analyzed 80,660 single-nucleus transcriptomes from postmortem prefrontal cortex of 48 ROSMAP participants with little, no, or varying Alzheimer's disease pathology. It defined major brain cell types and 40 transcriptionally distinct subpopulations, then linked pathology and sex to cell-type-specific expression programs involving myelination, inflammation, neuronal survival, and global stress response.

## Hypothesis framed
Alzheimer's disease pathology is associated with distinct, cell-type-specific and sex-specific transcriptional states in human prefrontal cortex, with recurrent disruption of myelination-related programs across multiple brain cell types.

## Questions answered
- Which major human prefrontal cortex cell types and transcriptional subpopulations are associated with Alzheimer's disease pathology in single-nucleus RNA-seq data?
- Do Alzheimer's disease-associated transcriptional changes differ between early and late pathological progression?
- Are Alzheimer's disease-associated cell states and transcriptional responses different between female and male cells?

## Key findings
Across excitatory neurons, inhibitory neurons, astrocytes, oligodendrocytes, oligodendrocyte precursor cells, and microglia, the study identified 40 transcriptionally distinct subpopulations, including pathology-associated subpopulations. The strongest disease-associated transcriptional changes appeared early in pathological progression and were highly cell-type specific, whereas late-stage upregulated genes were more shared across cell types and enriched for global stress-response pathways. Female cells were overrepresented in disease-associated subpopulations, sex-specific transcriptional responses were prominent in several cell types including oligodendrocytes, and myelination-related processes were recurrently perturbed across oligodendrocytes, OPCs, neurons, and other glia.

## Methods used
Single-nucleus RNA sequencing of postmortem prefrontal cortex, major cell-type annotation, clustering and subclustering to identify transcriptional subpopulations, pathology-associated differential expression analysis, sex-stratified transcriptional analysis, subpopulation enrichment analysis, and pathway/program interpretation of disease-associated genes.

## Method and dataset
The study used single-nucleus RNA-seq on 80,660 nuclei from prefrontal cortex tissue of 48 older ROSMAP participants, including 24 individuals with little or no Alzheimer's pathology and 24 with varying Alzheimer's-associated pathology. Participants were balanced by sex and matched for age and education, and nuclei were analyzed across six major brain cell classes. The analysis assumes that nuclear transcriptomes from postmortem prefrontal cortex preserve disease-relevant cell-type transcriptional states and that pathology-associated comparisons are interpretable after matching and cell-type stratification.

## Limitations
The study was observational and used postmortem tissue, so it cannot establish causality between transcriptional states and Alzheimer's disease progression. Samples were from prefrontal cortex only, limiting inference to other affected brain regions. The cohort consisted of elderly ROSMAP participants, which may limit generalizability. Single-nucleus RNA-seq captures nuclear transcripts rather than full cellular RNA, and inferred states may be affected by end-stage disease, postmortem effects, or tissue processing. The no-pathology comparison group included some individuals with cognitive impairment, complicating separation of pathology-specific and cognition-related effects.

## Evidence pattern
Entity definition: six major brain cell types and 40 transcriptionally distinct subpopulations were defined from single-nucleus transcriptomes. Comparison design: postmortem prefrontal cortex nuclei from 24 low/no-pathology individuals were compared with nuclei from 24 individuals with varying Alzheimer's pathology, with participants balanced by sex and matched for age and education. Statistical unit: individual nuclei were analyzed within cell types and subpopulations, with disease-pathology and sex-associated transcriptional patterns interpreted across individuals. Effect metrics: disease-associated differential expression, subpopulation association or overrepresentation, and pathway enrichment were used; exact numerical effect sizes are not provided in the summary. Covariates/controls: pathology status, sex balance, age matching, and education matching were described. Validation/boundary: the evidence is primary single-nucleus transcriptomic evidence without independent cross-cohort, spatial, protein-level, histological, or functional validation in the summary.

## Extends or contradicts
This study extends bulk-tissue and neuron- or microglia-focused Alzheimer's disease transcriptomic studies by resolving pathology-associated transcriptional changes across excitatory neurons, inhibitory neurons, astrocytes, oligodendrocytes, OPCs, and microglia. It does not directly contradict any listed prior wiki paper.

## Boundary conditions
Works when: Findings apply to human postmortem prefrontal cortex single-nucleus RNA-seq from elderly individuals with measured Alzheimer's disease pathology, sufficient nuclei to stratify major brain cell types, and study designs that compare pathology levels while accounting for sex and matched demographic factors.
Fails when: The study does not establish causal gene function, does not validate inferred states spatially or at protein level, and does not demonstrate reproducibility in an independent cohort or in brain regions beyond prefrontal cortex. Conclusions may fail to generalize to non-elderly populations, non-ROSMAP cohorts, earlier living disease stages, cytoplasmic RNA programs not captured by nuclei, or cell states sensitive to postmortem and tissue-processing artifacts.
