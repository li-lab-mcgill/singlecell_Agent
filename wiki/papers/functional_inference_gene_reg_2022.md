---
paper_id: functional_inference_gene_reg_2022
title: "Functional inference of gene regulation using single-cell multi-omics."
doi: "10.1016/j.xgen.2022.100166"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9534481/"
source_ids: {doc_id: "pmc:9534481", pmid: "36204155", pmcid: "9534481", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "atac_peak_to_gene", "multi_grn_inference"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Determine which computational method classes are used to integrate paired snRNA-seq and snATAC-seq and infer peak-to-gene or cis-regulatory links from the same cells, and what assumptions they make."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This paper profiles approximately 91,000 human peripheral blood mononuclear cells with scRNA-seq and scATAC-seq under DMSO, LPS, IFN-gamma, and PMA plus ionomycin stimulation across 1-hour and 6-hour time points. It introduces FigR, a computational framework that pairs separately profiled single-cell ATAC and RNA data, links distal accessible peaks to genes, identifies domains of regulatory chromatin, and infers enhancer-aware gene-regulatory networks.

## Hypothesis framed
Single-cell chromatin accessibility and gene expression profiles from stimulated immune cells can be computationally integrated to infer functional distal cis-regulatory elements, target genes, and transcription factor-driven regulatory networks underlying rapid immune responses.

## Questions answered
- Can separately generated scATAC-seq and scRNA-seq profiles from stimulated human blood cells be computationally paired to infer regulatory relationships?
- Can correlated single-cell chromatin accessibility and RNA dynamics identify distal peak-to-gene links and domains of regulatory chromatin during immune stimulation?
- Can enhancer-aware integration of scATAC-seq and scRNA-seq nominate transcription factors controlling stimulation-responsive immune gene programs?

## Key findings
Human immune stimulation induced rapid, cell-type-specific changes in chromatin accessibility and gene expression, including changes detectable on minute-scale timescales. FigR identified stimulation-associated domains of regulatory chromatin and linked distal accessible elements to transcriptional responses. The inferred stimulation gene-regulatory networks nominated candidate transcription factors regulating immune-response programs and connected transcription factor activity to disease-associated regulatory regions.

## Methods used
Single-cell RNA-seq and single-cell ATAC-seq profiling of human peripheral blood mononuclear cells; ex vivo stimulation with DMSO control, LPS, IFN-gamma, or PMA plus ionomycin for 1 or 6 hours; additional 6-hour Golgi inhibitor conditions; computational pairing of scATAC-seq and scRNA-seq cells using FigR; correlation-based distal peak-to-gene linkage; identification of domains of regulatory chromatin; enhancer-aware transcription factor gene-regulatory network inference.

## Method and dataset
FigR was applied to approximately 91,000 single-cell profiles from human peripheral blood mononuclear cells assayed by scRNA-seq and scATAC-seq across immune cell types, stimulation conditions, and time points. The method assumes that separately profiled ATAC and RNA cells can be computationally matched, that covariation between chromatin accessibility at distal peaks and gene expression across single cells reflects cis-regulatory linkage, and that transcription factor regulatory activity can be inferred statistically from enhancer accessibility and RNA dynamics.

## Limitations
The scATAC-seq and scRNA-seq profiles were computationally paired rather than directly measured in the same cell for all analyses, creating potential matching uncertainty. Peak-to-gene and transcription factor-gene links are statistical predictions and do not establish causality without experimental validation. The experiments used peripheral blood cells from a limited number of healthy donors and selected ex vivo stimulation conditions, so the results may not generalize to all immune contexts, disease states, tissue environments, or long-term regulatory responses.

## Evidence pattern
Entity definition: defines FigR, domains of regulatory chromatin, distal peak-to-gene links, and enhancer-aware gene-regulatory networks. Statistical unit: single cells from scRNA-seq and scATAC-seq profiles of human PBMCs. Analysis used: computational cross-modality cell pairing, correlation of chromatin accessibility and gene expression dynamics, DORC identification, and transcription factor network inference. Boundary conditions: evaluated in human blood immune cells under acute ex vivo stimulation. Validation: supported by consistency of inferred regulatory programs with stimulation-responsive genes, transcription factor activity, and disease-associated regulatory regions, but causal perturbation validation was not reported in the summary.

## Extends or contradicts


## Boundary conditions
Works when: Applies to single-cell datasets with both scATAC-seq and scRNA-seq profiles collected from comparable cell populations, conditions, and time points, where enough shared biological variation exists to computationally match cells and correlate distal chromatin accessibility with gene expression. Demonstrated on approximately 91,000 human PBMC profiles across multiple immune cell types and acute stimulation conditions.
Fails when: May fail or become unreliable when RNA and ATAC profiles come from non-overlapping cell populations, poorly matched conditions, very sparse or small datasets, weak regulatory variation, or contexts where correlation between accessibility and expression is insufficient to distinguish direct cis-regulation from indirect or secondary effects. It does not by itself prove causal enhancer-gene or transcription factor-gene relationships.
