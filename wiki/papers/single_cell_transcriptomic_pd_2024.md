---
paper_id: single_cell_transcriptomic_pd_2024
title: "Single-cell transcriptomic and proteomic analysis of Parkinson's disease brains."
doi: "10.1126/scitranslmed.abo1997"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12372474/"
source_ids: {doc_id: "pmc:12372474", pmid: "39475571", pmcid: "12372474", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_cell_type_annotation", "rna_differential_expression", "rna_differential_abundance"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["Learn which brain cell populations and disease-associated cellular states are reproducibly implicated in human Alzheimer's disease single-cell/nucleus transcriptomics, and how those states are biologically defined and validated."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study profiled postmortem human dorsolateral prefrontal cortex from six late-stage Parkinson's disease cases and six age- and sex-matched controls using single-nucleus RNA-seq, label-free quantitative mass spectrometry proteomics, and Lewy body pathology assessment. It identified PD-associated cell-type-specific transcriptional changes, elevated brain-resident T cells, reduced neuron-astrocyte interactions, synaptic protein down-regulation, and glial but not neuronal overlap with an Alzheimer's disease single-cell dataset.

## Hypothesis framed
Late-stage Parkinson's disease brains contain cell-type-specific transcriptomic and proteomic alterations in the prefrontal cortex, including inflammatory and glial changes, that relate to Lewy body pathology and differ from Alzheimer's disease neuronal vulnerability patterns.

## Questions answered
- Which major brain cell types and disease-associated transcriptional changes are detectable by single-nucleus RNA-seq in late-stage Parkinson's disease prefrontal cortex?
- Is alpha-synuclein/Lewy body pathology associated with specific cell-type transcriptional programs in the same postmortem PD tissues?
- Do Parkinson's disease and Alzheimer's disease prefrontal cortex single-cell datasets share neuronal or glial differentially expressed genes?

## Key findings
Analysis of 77,384 nuclei from six PD and six control prefrontal cortex samples identified eight major brain cell types: excitatory neurons, inhibitory neurons, astrocytes, microglia, oligodendrocytes, oligodendrocyte precursor cells, endothelial cells, and brain-resident T cells. Brain-resident T cells were elevated in PD. Alpha-synuclein/Lewy body pathology was inversely correlated with chaperone expression in excitatory neurons. Cell-cell interaction analysis indicated reduced neuron-astrocyte interactions and enhanced inflammatory signaling in PD. Proteomics of the same brains found preferential down-regulation of synaptic proteins in PD prefrontal cortex. Comparison with a published Alzheimer's disease prefrontal cortex single-cell dataset found no shared neuronal differentially expressed genes but many shared glial differentially expressed genes.

## Methods used
Single-nucleus RNA sequencing of postmortem dorsolateral prefrontal cortex, major cell-type and subcluster annotation, differential expression analysis, differential abundance assessment, cell-cell interaction inference, gene network analysis, Lewy body pathology quantification, label-free quantitative mass spectrometry-based proteomics, and cross-disease comparison with a published Alzheimer's disease prefrontal cortex single-cell dataset.

## Method and dataset
The study used single-nucleus RNA-seq on 77,384 nuclei from dorsolateral prefrontal cortex of six late-stage PD cases and six age- and sex-matched controls, combined with label-free quantitative proteomics and Lewy body pathology assessment from the same brains. The design assumes that postmortem prefrontal cortex nuclei capture disease-associated cellular states, that disease-control differences can be estimated from the matched cohort, and that inferred ligand-receptor or cell-cell interaction changes reflect altered communication programs rather than direct measured signaling.

## Limitations
The cohort was small, with six PD and six control brains, limiting statistical power and generalizability. Samples were late-stage postmortem tissues, so findings may not represent early or causal PD events. The analysis focused on prefrontal cortex rather than classic PD-vulnerable regions such as substantia nigra. Postmortem tissue quality, clinical heterogeneity, medication history, agonal factors, and lack of blinding to disease status may influence results. Most findings are correlative and require functional validation in independent cohorts and experimental models.

## Evidence pattern
Comparison design: six late-stage PD brains versus six age- and sex-matched control brains profiled in the same prefrontal cortex region. Entity definition: nuclei were clustered and annotated into eight major brain cell types, including neuron, glial, vascular, and T cell populations. Analysis used: cell-type-specific differential expression, differential abundance, pathology correlation, inferred cell-cell interactions, proteomics, and comparison to a published AD prefrontal cortex dataset. Validation or orthogonal support: proteomics from the same brains supported synaptic protein down-regulation; Lewy body pathology was measured in the same tissues. Boundary condition: evidence supports late-stage PD prefrontal cortex and cross-disease comparison at the level of differentially expressed genes, not direct validation of AD-associated cellular states.

## Extends or contradicts
The study extends prior human neurodegeneration single-cell findings by showing that PD and AD prefrontal cortex share many glial differentially expressed genes but do not share neuronal differentially expressed genes, supporting overlap in glial inflammatory responses and divergence in neuronal vulnerability programs.

## Boundary conditions
Works when: Findings apply to postmortem human dorsolateral prefrontal cortex from late-stage PD cases and matched controls profiled with snRNA-seq at approximately 80,000 nuclei, with parallel bulk proteomics and tissue pathology available from the same brains. The PD-versus-AD comparison applies when using comparable published single-cell data from similar prefrontal cortex regions and comparing cell-type-specific differentially expressed genes.
Fails when: Findings may not apply to early PD, prodromal PD, living tissue, substantia nigra or other primary PD-affected regions, cohorts with different medication or agonal histories, or analyses requiring causal inference. The study does not provide direct validation of AD-specific disease-associated cell states, replication across independent AD single-cell datasets, or functional proof that the inferred neuron-astrocyte and inflammatory interaction changes drive pathology.
