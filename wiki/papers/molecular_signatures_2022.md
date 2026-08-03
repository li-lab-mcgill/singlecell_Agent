---
paper_id: molecular_signatures_2022
title: "Molecular signatures underlying neurofibrillary tangle susceptibility in Alzheimer's disease."
doi: "10.1016/j.neuron.2022.06.021"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9509477/"
source_ids: {doc_id: "pmc:9509477", pmid: "35882228", pmcid: "9509477", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_cell_type_annotation", "rna_differential_expression", "rna_gene_programs"]
retrieval_goals: ["broad_background"]
retrieval_intents: ["Understand how prior human single-cell AD studies define disease-relevant cell types and states in prefrontal cortex, and what biological programs a credible analysis should recover."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study developed a high-throughput single-soma RNA-seq workflow to isolate and profile NFT-bearing and NFT-free neuronal somas from fresh-frozen human Alzheimer’s disease brain. It classified 20 neocortical neuronal subtypes, quantified subtype-specific NFT susceptibility and neuronal loss, and identified shared and subtype-specific transcriptional programs associated with neurofibrillary tangle status.

## Hypothesis framed
Neuronal susceptibility to tau aggregation into neurofibrillary tangles in Alzheimer’s disease is associated with specific transcriptional states that differ between aggregation-prone and aggregation-resistant neocortical neuronal subtypes.

## Questions answered
- Which neocortical neuronal subtypes are most susceptible to neurofibrillary tangle formation and neuronal loss in Alzheimer’s disease?
- What transcriptional programs distinguish NFT-bearing neurons from NFT-free neurons in the same human AD brain tissues?
- Are NFT-bearing neurons characterized by a universal apoptotic or mitochondrial dysfunction program, or by subtype-specific stress and synaptic programs?

## Key findings
NFT susceptibility varied substantially across 20 neocortical neuronal subtypes. NFT-bearing neurons shared strong upregulation of synaptic transmission-related genes, including a core set of 63 genes enriched for synaptic vesicle cycling. Oxidative phosphorylation and mitochondrial dysfunction signatures were highly cell-type dependent rather than universal. Apoptosis-related programs were only modestly enriched, and estimated susceptibility to death was highly similar between NFT-bearing and NFT-free neurons.

## Methods used
Gentle mechanical dissociation of fresh-frozen human brain, density-gradient enrichment, fluorescence-activated cell sorting, isolation of single neuronal somas while preserving NFT status, single-cell/single-soma RNA sequencing, transcriptomic classification of neocortical neuronal subtypes, subtype-specific estimation of NFT susceptibility and neuronal loss, and differential gene-expression and gene-program analysis comparing NFT-bearing versus NFT-free neurons.

## Method and dataset
Single neuronal somas from fresh-frozen postmortem human brain, including prefrontal cortex and other regions from neuropathologically confirmed Alzheimer’s disease donors and cognitively normal controls, were profiled by single-soma RNA sequencing. NFT-bearing and NFT-free somas were processed in parallel from the same tissues, and transcriptomes were assigned to 20 neocortical neuronal subtypes. The summary does not report the number of donors or profiled somas. The design assumes that NFT status can be preserved during soma isolation and that transcriptomes remaining after freeze-thaw cytoplasmic RNA loss are sufficient for subtype assignment and differential expression analysis.

## Limitations
Fresh-frozen tissue processing and freeze-thaw disruption caused loss of many cytoplasmic transcripts, which may affect transcript quantification and cell recovery. Variable cytoplasmic RNA loss may remain despite parallel processing of NFT-bearing and NFT-free somas. Postmortem human tissue captures late-stage molecular states rather than dynamic causal processes. AD donors were advanced-stage cases, limiting generalization to early disease. The study focused on neuronal NFT/tau-associated states and did not provide a broad pan-cell-type atlas of glial, vascular, amyloid-associated, inflammatory, or myelination programs. Original code was not reported, although data were deposited publicly.

## Evidence pattern
Entity definition: NFT-bearing and NFT-free single neuronal somas were directly isolated and profiled. Comparison design: NFT-bearing versus NFT-free somas processed in parallel from the same tissues, with AD donors and cognitively normal controls. Statistical unit: single neuronal soma assigned to one of 20 neocortical neuronal subtypes. Effect metrics: subtype-specific NFT susceptibility, estimated neuronal loss, and differential gene-expression/gene-program enrichment. Covariates and controls: parallel processing from the same tissues to reduce donor-specific confounding. Boundary conditions: postmortem advanced AD brain and fresh-frozen tissue with cytoplasmic RNA loss.

## Extends or contradicts
Extends prior human single-cell Alzheimer’s disease studies by adding direct NFT-status information to single-neuron transcriptomes, which standard single-nucleus RNA-seq cannot determine. The findings argue against a simple universal apoptotic program in NFT-bearing neurons and instead support cell-type-specific responses involving synaptic dysfunction and stress.

## Boundary conditions
Works when: Applies to fresh-frozen postmortem human brain samples where neuronal somas can be mechanically isolated, enriched, sorted, and profiled while preserving NFT-bearing versus NFT-free status. Most relevant for advanced Alzheimer’s disease tissue and analyses focused on neuronal tau/NFT-associated transcriptional states in neocortical subtypes.
Fails when: Does not address early disease trajectories or causal ordering of transcriptional states. Does not define broad non-neuronal AD states such as astrocyte, microglial, oligodendrocyte, OPC, endothelial, inflammatory, amyloid-associated, or myelination programs. Transcript quantification may be unreliable for cytoplasmic RNAs lost during freeze-thaw processing, and findings may not generalize to non-neocortical regions or early-stage AD without validation.
