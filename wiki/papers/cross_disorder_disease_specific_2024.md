---
paper_id: cross_disorder_disease_specific_2024
title: "Cross-disorder and disease-specific pathways in dementia revealed by single-cell genomics."
doi: "10.1016/j.cell.2024.08.019"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12017262/"
source_ids: {doc_id: "pmc:12017262", pmid: "39265576", pmcid: "12017262", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_differential_abundance", "rna_differential_expression", "atac_grn_inference"]
retrieval_goals: ["broad_background"]
retrieval_intents: ["Understand how prior human single-cell AD studies define disease-relevant cell types and states in prefrontal cortex, and what biological programs a credible analysis should recover."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study profiled postmortem human brain nuclei from Alzheimer's disease, behavioral-variant frontotemporal dementia with Pick's disease pathology, progressive supranuclear palsy, and non-demented controls using single-nucleus RNA-seq and ATAC-seq. It compared three cortical regions across 41 participants and approximately 1 million RNA plus ATAC nuclei to define shared and disease-specific dementia-associated cell states, selective neuronal vulnerability, and disease-associated regulatory networks.

## Hypothesis framed
Major dementias share some glial-immune and neurodegenerative molecular programs but also have disease-specific cell states, selectively vulnerable neuronal subclasses, and distinct gene-regulatory networks that can be resolved by single-nucleus RNA-seq and ATAC-seq across vulnerable and relatively resilient human brain regions.

## Questions answered
- Which disease-associated cell types and cell states are shared across Alzheimer's disease, frontotemporal dementia with Pick's disease pathology, and progressive supranuclear palsy?
- Which excitatory neuronal populations show disease-specific vulnerability in Alzheimer's disease, frontotemporal dementia, and progressive supranuclear palsy?
- Do RNA and chromatin-accessibility profiles identify disease-associated gene-regulatory networks and causal genetic-risk-affected cell types that differ by dementia subtype?

## Key findings
The study identified 32 disease-associated cell types shared across dementias and 14 disease-specific cell states. Shared disease-associated alterations included glial and immune-related changes, while disease-specific vulnerability affected layer 5 intratelencephalic neurons in Alzheimer's disease, layer 2/3 intratelencephalic neurons in frontotemporal dementia, and layer 5/6 near-projecting neurons in progressive supranuclear palsy. RNA and ATAC analyses identified disease-associated gene-regulatory networks and showed that regulatory drivers and cells affected by causal genetic risk differ by disorder; OPCML and KCNH7 were enriched in vulnerable excitatory neuronal populations across disorders.

## Methods used
Postmortem single-nucleus RNA-seq, single-nucleus ATAC-seq on a subset of samples, cell-type annotation, cross-disorder comparison, disease-associated cell-state analysis, differential gene-expression analysis, chromatin-accessibility analysis, gene-regulatory network inference, and assessment of disease-risk gene effects across cell types.

## Method and dataset
The analysis used frozen postmortem brain tissue from 41 individuals: 10 Alzheimer's disease cases, 10 behavioral-variant frontotemporal dementia cases with Pick's disease pathology, 11 progressive supranuclear palsy cases, and 10 non-demented controls. Primary motor cortex, primary visual cortex, and insular cortex were profiled; approximately 880,000 snRNA-seq nuclei were generated, about 590,000 high-quality transcriptomes were retained after quality control, and snATAC-seq was generated from a subset of samples. The design assumes that nuclear transcriptomes and chromatin accessibility from postmortem tissue capture disease-relevant cell states and that cross-disorder case-control comparisons across the profiled cortical regions can separate shared dementia programs from disease-specific effects.

## Limitations
The study is cross-sectional and based on postmortem tissue, so it cannot directly establish temporal sequence or causality. Cohort size was relatively small within each disease group, some samples failed quality control or were removed as outliers, and only primary motor cortex, primary visual cortex, and insular cortex were profiled. snRNA-seq and snATAC-seq measure nuclear RNA and chromatin accessibility rather than protein abundance, cellular physiology, or direct functional consequences, and the selected dementia subtypes may not generalize to all neurodegenerative diseases or stages.

## Evidence pattern
Entity definition: disease-associated cell types and disease-specific cell states were defined from single-nucleus RNA profiles across annotated cell populations. Comparison design: Alzheimer's disease, behavioral-variant frontotemporal dementia with Pick's disease pathology, progressive supranuclear palsy, and non-demented controls were compared across three cortical regions with differing vulnerability. Statistical unit: nuclei nested within postmortem donors, disease groups, cell types, and brain regions. Analysis used: cell-type annotation, differential abundance or cell-state analysis, differential gene expression, chromatin-accessibility analysis, gene-regulatory network inference, and disease-risk gene assessment. Boundary conditions: conclusions apply to the profiled cortical regions and diagnostic groups.

## Extends or contradicts
This study extends prior Alzheimer's disease single-cell findings by testing whether disease-associated neuronal, glial, immune, and regulatory programs are Alzheimer's-specific or shared across frontotemporal dementia and progressive supranuclear palsy. It does not directly analyze prefrontal or dorsolateral prefrontal cortex and does not directly map results to the Mathys et al. 2019 Nature Alzheimer's disease single-cell states in the provided summary.

## Boundary conditions
Works when: Findings are most applicable to human postmortem frozen cortical brain samples from Alzheimer's disease, behavioral-variant frontotemporal dementia with Pick's disease pathology, progressive supranuclear palsy, and non-demented controls when single-nucleus RNA-seq is available across multiple donors and cortical regions, and when snATAC-seq is available to support chromatin-accessibility and regulatory-network analyses.
Fails when: The findings may not apply to living-cell physiology, protein-level mechanisms, longitudinal disease progression, non-cortical regions, prefrontal or dorsolateral prefrontal cortex-specific programs, dementia subtypes not profiled, or cohorts too small or low-quality to distinguish donor, region, disease, and cell-type effects.
