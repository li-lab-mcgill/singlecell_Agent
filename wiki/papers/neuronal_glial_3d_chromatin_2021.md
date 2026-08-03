---
paper_id: neuronal_glial_3d_chromatin_2021
title: "Neuronal and glial 3D chromatin architecture informs the cellular etiology of brain disorders."
doi: "10.1038/s41467-021-24243-0"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC8233376/"
source_ids: {doc_id: "pmc:8233376", pmid: "34172755", pmcid: "8233376", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "atac_peak_to_gene"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["Learn what prior single-cell chromatin or multiome studies have shown about AD-associated CREs, enhancer accessibility, and cell-type-specific genetic risk in human brain."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study generated neuron-enriched and glia-enriched Hi-C maps from adult human dorsolateral prefrontal cortex and integrated them with nuclear RNA-seq, H3K27ac enhancer profiles, and disease genetic and epigenetic datasets. It used cell-type-specific 3D chromatin architecture to connect non-coding regulatory elements to genes and to infer which brain cell types are implicated by Alzheimer's disease, schizophrenia, and bipolar disorder risk signals.

## Hypothesis framed
Cell-type-specific 3D chromatin architecture in human neurons and glia can identify enhancer-gene regulatory landscapes that distinguish the cellular mechanisms of epigenetic dysregulation and inherited genetic risk in major brain disorders.

## Questions answered
- Do neuronal and glial nuclei from adult human dorsolateral prefrontal cortex show reproducible, cell-type-specific 3D chromatin organization?
- Are Alzheimer's disease-associated epigenetic dysregulation and inherited Alzheimer's genetic risk enriched in the same or different brain cell-type regulatory landscapes?
- Which neuronal subtype regulatory maps are most enriched for schizophrenia and bipolar disorder genetic risk?

## Key findings
Hi-C profiles clustered by cell type rather than individual, supporting reproducible neuron- and glia-specific 3D genome organization. Thousands of genomic regions switched chromatin compartments between neurons and glia, and these compartment switches were associated with cell-type-specific gene expression, including neuronal genes in neuronal-active compartments and glial genes in glial-active compartments. Alzheimer's disease-associated epigenetic dysregulation mapped mainly to neurons and oligodendrocytes, whereas inherited Alzheimer's disease genetic risk was more strongly connected to microglial regulatory landscapes. Schizophrenia and bipolar disorder genetic risk both implicated parvalbumin-expressing interneurons, while bipolar disorder was more associated with upper-layer neurons and schizophrenia with deeper-layer projection neurons.

## Methods used
Hi-C on NeuN-positive neuronal nuclei and NeuN-negative glial-enriched nuclei from adult human dorsolateral prefrontal cortex; integration with nuclear RNA-seq, H3K27ac enhancer profiles, cell-type enhancer maps, disease epigenetic datasets, and GWAS risk loci; identification of chromatin compartments, frequently interacting regions, chromatin loops, and cell-type-specific regulatory domains; enhancer-to-gene linking using chromatin contacts; enrichment analyses connecting regulatory landscapes to Alzheimer's disease, schizophrenia, and bipolar disorder signals.

## Method and dataset
The study used genome-wide chromosome conformation capture data from purified NeuN-positive and NeuN-negative adult human dorsolateral prefrontal cortex nuclei, integrated with nuclear RNA-seq and enhancer-associated H3K27ac profiles. The summary does not specify donor count, nuclei count, sequencing depth, or exact number of Hi-C libraries. The design compared broad neuronal versus glial-enriched nuclear populations, then refined neuronal subtype interpretation using external glutamatergic and GABAergic enhancer profiles. The analysis assumes that chromatin contacts and enhancer marks in purified populations can assign non-coding regulatory elements to putative target genes and that enrichment of disease-associated variants or epigenetic alterations in those regulatory maps reflects likely disease-relevant cell types.

## Limitations
The primary Hi-C maps were generated from broad NeuN-positive and NeuN-negative populations rather than fully resolved individual brain cell types. NeuN-negative nuclei are glial-enriched but contain multiple cell classes, especially oligodendrocytes, and may not fully represent astrocytes or microglia. Hi-C sample size was limited according to the summary, and tissue was mainly adult dorsolateral prefrontal cortex, so findings may not generalize to development or other disease-relevant brain regions. Disease conclusions are based on integrative enrichment and regulatory-linking analyses and do not prove causal enhancer-gene relationships or cell-type-specific disease mechanisms. The study did not directly generate single-nucleus ATAC-seq or multiome chromatin accessibility profiles.

## Evidence pattern
Entity definition: NeuN-positive nuclei were treated as neuronal and NeuN-negative nuclei as glial-enriched; regulatory elements were defined using Hi-C contacts, chromatin compartments, FIREs, loops, H3K27ac enhancer profiles, and external cell-type enhancer maps. Comparison design: neuronal versus glial-enriched chromatin architecture across adult human dorsolateral prefrontal cortex samples, followed by disease enrichment analyses for Alzheimer's disease, schizophrenia, and bipolar disorder. Statistical unit: genomic regions, chromatin compartments, loops, regulatory domains, enhancer-gene links, disease-associated loci, and broad purified nuclear cell classes. Metrics: clustering of Hi-C profiles by cell type, compartment switching, cell-type-specific expression association, regulatory enrichment of epigenetic dysregulation, and enrichment of GWAS risk loci in cell-type regulatory maps. Validation: reproducibility across individuals and concordance with RNA-seq, H3K27ac enhancer profiles, and known cell-type gene expression patterns. Boundary conditions: findings are strongest for adult human dorsolateral prefrontal cortex and broad neuronal/glial regulatory landscapes, with subtype inference dependent on external enhancer and transcriptomic data.

## Extends or contradicts
This paper extends prior bulk brain non-coding risk interpretation by adding neuron- and glia-specific 3D chromatin maps that connect regulatory elements to putative target genes. It supports the distinction that Alzheimer's disease epigenetic dysregulation points to neurons and oligodendrocytes, while inherited Alzheimer's disease genetic risk points more strongly to microglia.

## Boundary conditions
Works when: Applies when purified or enriched human brain nuclear populations are available for chromatin conformation profiling and when disease-associated non-coding loci can be interpreted through cell-type regulatory maps. The disease-risk enrichment conclusions are most applicable to adult human dorsolateral prefrontal cortex and to broad NeuN-positive neuronal and NeuN-negative glial-enriched regulatory landscapes supplemented by external enhancer or transcriptomic annotations.
Fails when: Does not provide direct single-cell or single-nucleus accessibility measurements, so it is not sufficient for fine-resolution CRE accessibility comparisons across microglia, astrocytes, oligodendrocytes, excitatory neurons, and inhibitory neurons. It is not designed to test disease versus control chromatin accessibility in Alzheimer's disease brain tissue, to functionally validate enhancer-target gene pairs at specific loci, or to resolve developmental-stage-specific or brain-region-specific disease mechanisms outside the sampled adult dorsolateral prefrontal cortex context.
