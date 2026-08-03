---
paper_id: single_nucleus_multiomics_2024
title: "Single-nucleus multiomics reveals the disrupted regulatory programs in three brain regions of sporadic early-onset Alzheimer's disease."
doi: "10.1101/2024.06.25.600720"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC11230393/"
source_ids: {doc_id: "pmc:11230393", pmid: "38979371", pmcid: "11230393", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_differential_accessibility", "atac_peak_to_gene", "multi_grn_inference"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["Learn what prior single-cell chromatin or multiome studies have shown about AD-associated CREs, enhancer accessibility, and cell-type-specific genetic risk in human brain."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study generated a 10x Genomics single-nucleus RNA+ATAC multiome atlas from postmortem prefrontal cortex, entorhinal cortex, and hippocampus of individuals with sporadic early-onset Alzheimer's disease and controls. It identified cell type- and brain region-specific transcriptomic and chromatin-accessibility changes, linked candidate cis-regulatory elements to sEOAD-associated genes, prioritized glial transcription factor programs, and related sEOAD cCREs to late-onset AD and neuropsychiatric disorder risk loci.

## Hypothesis framed
Sporadic early-onset Alzheimer's disease disrupts cell type-specific transcriptional and chromatin regulatory programs across vulnerable human brain regions, and disease-associated candidate cis-regulatory elements can reveal glial regulators and overlap genetic risk loci for Alzheimer's disease and related neuropsychiatric disorders.

## Questions answered
- Which cell type- and brain region-specific transcriptomic and chromatin-accessibility changes are associated with sporadic early-onset Alzheimer's disease in human prefrontal cortex, entorhinal cortex, and hippocampus?
- Which candidate cis-regulatory elements are linked to sEOAD-associated genes, and do any overlap known late-onset Alzheimer's disease risk loci?
- Which transcription factors are prioritized as conserved glial regulators of sEOAD-associated gene programs across multiple brain regions?

## Key findings
Across more than 71,000 nuclei from four sEOAD cases and five controls, the study found cell type- and region-specific changes in gene expression and chromatin accessibility. It prioritized seven conserved transcription factors in glial cells across multiple brain regions, including RFX4 in astrocytes and IKZF1 in microglia, as candidate regulators of sEOAD-associated genes. RFX4-linked astrocyte programs were associated with transmembrane transport and trans-synaptic signaling, while microglial regulatory changes implicated neuroinflammatory pathways. The authors identified the top 25 altered intercellular signaling interactions between glial cells and neurons and reported 38 cCREs linked to sEOAD-associated genes that overlapped late-onset AD risk loci; sEOAD cCREs were also enriched in neuropsychiatric disorder risk loci.

## Methods used
10x Genomics single-nucleus multiome sequencing of matched RNA expression and chromatin accessibility from postmortem human brain nuclei; quality control and analysis of more than 71,000 nuclei; major brain cell type and subtype annotation; disease-associated differential gene expression analysis; disease-associated candidate cis-regulatory element and chromatin-accessibility analysis; peak-to-gene or cCRE-to-gene linking; transcription factor regulon inference; altered glia-neuron cell-cell communication analysis; overlap and enrichment analysis against late-onset AD and neuropsychiatric disorder genetic risk loci.

## Method and dataset
The dataset consisted of postmortem prefrontal cortex, entorhinal cortex, and hippocampus samples from nine donors: four neuropathologically confirmed sporadic early-onset Alzheimer's disease cases and five age-matched controls. The method jointly measured single-nucleus RNA expression and ATAC chromatin accessibility using 10x Genomics multiome sequencing and analyzed more than 71,000 nuclei. The experimental design compared sEOAD versus control nuclei within annotated brain cell types and brain regions. The regulatory analyses assume that disease-associated accessibility differences and expression-accessibility links in postmortem nuclei can nominate candidate cis-regulatory elements, target genes, and transcription factor programs, but these links are correlative rather than causal.

## Limitations
The cohort was small, with nine postmortem donors including only four sEOAD cases, limiting donor-level statistical power and generalizability. Findings are correlative and based on postmortem tissue, so they cannot distinguish disease-driving regulatory mechanisms from downstream disease consequences. The study examined only prefrontal cortex, entorhinal cortex, and hippocampus, and may miss regulatory changes in other affected brain regions. Prioritized transcription factors, enhancers, and signaling pathways require larger independent replication and functional perturbation validation.

## Evidence pattern
The entity definition was neuropathologically confirmed sporadic early-onset Alzheimer's disease, defined as onset before age 65 without known autosomal-dominant APP, PSEN1, or PSEN2 mutations, compared with age-matched controls. The comparison design contrasted sEOAD and control postmortem nuclei across three brain regions and annotated cell types. The statistical units for discovery were nuclei/cell-type-region groups, but disease inference was limited by nine donor-level biological replicates. Effect evidence included differentially expressed genes, altered chromatin-accessible cCREs, linked cCRE-gene pairs, prioritized TF regulons, altered cell-cell signaling interactions, and overlap/enrichment of cCREs with AD and neuropsychiatric disorder risk loci. Boundary conditions were human postmortem single-nucleus multiome data from prefrontal cortex, entorhinal cortex, and hippocampus in sEOAD.

## Extends or contradicts
This study extends prior Alzheimer's disease single-cell and single-nucleus work by adding paired RNA and chromatin accessibility profiling across three vulnerable brain regions specifically in sporadic early-onset Alzheimer's disease, and by linking sEOAD-associated cCREs to genes, glial TF programs, and late-onset AD genetic risk loci. No direct contradiction of an existing listed paper is indicated in the summary.

## Boundary conditions
Works when: Applies to human postmortem single-nucleus RNA+ATAC multiome datasets with matched expression and chromatin accessibility from disease and control donors, sufficient nuclei to annotate major brain cell types, and brain regions comparable to prefrontal cortex, entorhinal cortex, and hippocampus. The reported findings are most directly applicable to sporadic early-onset Alzheimer's disease cases without known autosomal-dominant APP, PSEN1, or PSEN2 mutations.
Fails when: The study does not establish causality for prioritized cCREs, transcription factors, or signaling interactions without functional perturbation. It has limited power for donor-level cell type-specific genetic risk analyses because the cohort includes only four sEOAD cases and five controls. It may not generalize to late-onset Alzheimer's disease, familial autosomal-dominant Alzheimer's disease, non-profiled brain regions, living tissue states, or datasets lacking paired RNA and ATAC measurements.
