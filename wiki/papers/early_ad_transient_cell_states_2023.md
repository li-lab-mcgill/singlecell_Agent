---
paper_id: early_ad_transient_cell_states_2023
title: "Early Alzheimer's disease pathology in human cortex involves transient cell states."
doi: "10.1016/j.cell.2023.08.005"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC11107481/"
source_ids: {doc_id: "pmc:11107481", pmid: "37774681", pmcid: "11107481", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_differential_abundance", "rna_differential_expression", "rna_gene_programs"]
retrieval_goals: ["contradiction"]
retrieval_intents: ["Find studies that report neuronal-dominant or early neuronal regulatory/transcriptomic changes in AD to check whether a blanket \"microglia strongest\" claim is overgeneralized."]
extends: []
added: 2026-05-27
session: unknown
---

## Summary
This study builds a single-nucleus RNA-seq atlas from fresh human frontal cortical biopsies from living adults with varying early AD pathology and integrates these data with 36 external datasets to identify cell states specific to early AD. It defines an Early Cortical Amyloid Response in which excitatory neurons enter a transitional hyperactive/hypermetabolic state preceding neuronal loss, microglia expand with neuroinflammatory programs, and amyloid-processing genes are upregulated in pyramidal neurons and oligodendrocytes, with electrophysiological validation of neuronal hyperexcitability.

## Background
Most AD cellular data are derived from postmortem tissue or model organisms, limiting resolution of transient early pathophysiological states. Identifying in vivo early cortical cell states is needed to guide early therapeutic strategies targeting circuit dysfunction, neuroinflammation, and amyloid production.

## Method and dataset
Single-nucleus RNA-seq was performed on fresh frontal cortex (BA8/9) biopsies obtained during shunt surgery from 52 adults with hydrocephalus and frozen within minutes to preserve in vivo transcriptional states. Samples were stratified by histopathology (Aβ+, Aβ+Tau+, or none) and related to CSF Aβ42, phosphorylated tau, and MMSE scores. The dataset was integrated with 36 datasets from 28 single-cell/nucleus studies (cross-disease, cross-species). Neuronal hyperexcitability was independently validated using acute slice electrophysiology on separate biopsy specimens. The study assumes rapid processing preserves transient cellular states and that cross-study integration adequately mitigates batch effects.

## Analysis
Defined cell types and states across neurons, microglia, astrocytes, and oligodendrocytes; performed differential expression within cell types across pathology strata; quantified cell-state abundance changes with increasing pathology; conducted pathway and gene program analysis to delineate an Early Cortical Amyloid Response; correlated biopsy pathology with CSF biomarkers and MMSE; validated neuronal hyperexcitability using acute slice electrophysiology; integrated across multiple external datasets to assess conservation and specificity of early AD-associated states.

## Key findings
An Early Cortical Amyloid Response (ECAR) specific to early AD pathology was identified across cell types. Excitatory neurons exhibited a transitional hyperactive, hypermetabolic state that preceded their loss, with hyperexcitability confirmed by acute slice electrophysiology. Astrocytes upregulated glutathione metabolism and fatty-acid degradation, consistent with altered synaptic homeostasis in response to increased neuronal activity. An upper-layer NDNF-expressing L1 interneuron population was selectively depleted early. Microglia expanded with increasing pathology and overexpressed neuroinflammatory programs. Pyramidal neurons and oligodendrocytes upregulated genes involved in β-amyloid production and processing during the early hyperactive phase. CSF biomarkers (Aβ42, phosphorylated tau) correlated with biopsy pathology, and Aβ+ individuals had lower MMSE scores than controls. Sampling site did not drive pathology burden, and cross-study integration indicated that these cell states are conserved and specific to early AD.

## Limitations
Cohort comprised hydrocephalus patients undergoing surgery, introducing potential selection and clinical-context biases; sampling limited to frontal cortex, reducing regional generalizability; cross-sectional design limits temporal causality; modest Aβ+Tau+ sample size; snRNA-seq captures nuclear transcripts and may miss cytoplasmic biology; residual technical confounds may remain despite integration; electrophysiological validation is ex vivo and may not fully capture in vivo dynamics; cohort predominantly older and of Finnish ancestry, potentially limiting population generalizability.

## Metrics used
Histopathology categories (Aβ+, Aβ+Tau+, none); CSF Aβ42 and phosphorylated tau levels; Mini-Mental State Examination (MMSE) scores; differential expression results within cell types; changes in cell/state abundance with pathology; pathway/gene program activation; electrophysiological readouts of neuronal hyperexcitability in acute cortical slices.
