---
paper_id: single_cell_atlas_2023
title: "Single-cell atlas reveals correlates of high cognitive function, dementia, and resilience to Alzheimer's disease pathology."
doi: "10.1016/j.cell.2023.08.039"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC10601493/"
source_ids: {doc_id: "pmc:10601493", pmid: "37774677", pmcid: "10601493", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_cell_type_annotation", "rna_differential_expression", "rna_differential_abundance"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["Learn which brain cell populations and disease-associated cellular states are reproducibly implicated in human Alzheimer's disease single-cell/nucleus transcriptomics, and how those states are biologically defined and validated."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study generated a single-nucleus RNA-seq atlas of the aged human prefrontal cortex using 2,359,994 nuclei from 427 ROSMAP postmortem brain donors with varying Alzheimer’s disease pathology and cognitive status. It links cell-type-specific transcriptional programs and cell abundance changes to AD pathology, dementia, high late-life cognitive function, and resilience to AD pathology.

## Hypothesis framed
Cell-type-specific transcriptional states and abundance shifts in the aged human prefrontal cortex are associated with cognitive function, dementia, and resilience to Alzheimer’s disease pathology.

## Questions answered
- Which prefrontal cortex cell types and subtypes show transcriptional changes associated with Alzheimer’s disease pathology?
- Which neuronal populations are depleted or enriched in association with dementia, high cognitive function, or resilience to Alzheimer’s disease pathology?
- Do individuals with preserved cognition despite Alzheimer’s disease pathology show distinct cell-type-specific molecular or compositional signatures?

## Key findings
Across 2,359,994 nuclei from 427 individuals, the study annotated 54 high-resolution cell types across 12 major brain cell groups. AD pathology was associated with shared transcriptional alterations across excitatory neuron subtypes, including pathways related to synaptic signaling, chromatin organization, lipid metabolism, RNA metabolism, and mitochondrial function. Excitatory neurons and oligodendrocytes showed a coordinated increase in cohesin complex components and DNA damage response factors during AD progression. Somatostatin inhibitory neuron subtypes were selectively depleted in AD, while two distinct inhibitory neuron groups were more abundant in individuals with preserved high cognitive function late in life, supporting a link between inhibitory neurons and cognitive resilience to AD pathology.

## Methods used
Single-nucleus RNA sequencing of postmortem prefrontal cortex, cell and nucleus quality control, clustering and annotation into major and subtype-level cell classes, cell-type-specific differential gene expression analyses, pathway analyses, and cell composition analyses relating transcriptomic states and cell-type abundance to AD pathology, dementia, high cognitive function, and resilience phenotypes.

## Method and dataset
The study used single-nucleus RNA-seq on postmortem prefrontal cortex tissue from 427 participants in the Religious Order Study and Rush Memory and Aging Project, analyzing 2,359,994 nuclei after quality control. The experimental design compared individuals spanning no cognitive impairment, mild cognitive impairment, and AD dementia, with varying degrees of AD neuropathology. The analysis assumes that nuclear transcriptomes from postmortem prefrontal cortex capture biologically meaningful cell identities and disease-associated states, and that cross-individual associations between cell-type expression or abundance and clinical/pathological phenotypes can identify correlates of dementia, high cognitive function, and resilience.

## Limitations
The study is based on postmortem cross-sectional tissue, so it cannot establish causality or temporal ordering of disease-associated cellular changes. Sampling was focused on aged human prefrontal cortex and may not represent other brain regions affected by AD. Single-nucleus RNA-seq measures transcript abundance rather than protein levels or cellular function. Tissue quality, agonal state, postmortem processing, demographic structure, genetic background, environmental factors, and comorbidities in ROSMAP participants may influence observed associations. Functional validation and comprehensive protein-level or spatial validation were limited for some implicated cell states.

## Evidence pattern
Entity definition: 54 high-resolution brain cell types across 12 major groups were defined from single-nucleus RNA-seq clustering and annotation. Comparison design: cell-type-specific expression and abundance were compared across AD pathology burden, dementia status, high cognitive function, and resilience to AD pathology. Statistical unit: nuclei were profiled, with disease and cognitive phenotypes defined at the donor level across 427 individuals. Effect metrics: differential gene expression, pathway enrichment, and cell-type composition changes were used to identify phenotype-associated states. Covariates: specific covariates were not described in the provided summary. Boundary conditions: conclusions are supported for aged human postmortem prefrontal cortex from ROSMAP donors.

## Extends or contradicts
This paper extends human Alzheimer’s disease single-cell transcriptomic evidence by providing a much larger postmortem prefrontal cortex atlas linked to detailed cognitive and neuropathological phenotypes. No direct contradiction of a listed prior wiki paper is specified in the summary.

## Boundary conditions
Works when: Findings apply to large-scale single-nucleus RNA-seq data from aged human postmortem prefrontal cortex with donor-level measures of AD neuropathology and cognitive status, especially when the design includes hundreds of individuals and enough nuclei to resolve neuronal subtypes such as somatostatin inhibitory neurons.
Fails when: Findings do not establish causality, temporal progression, protein-level mechanisms, or cellular function. They may not generalize to non-prefrontal brain regions, younger cohorts, non-ROSMAP populations, living tissue, spatially resolved tissue architecture, or datasets without sufficient donor numbers and subtype resolution to detect cell-type-specific abundance and expression associations.
