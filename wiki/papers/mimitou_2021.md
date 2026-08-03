---
paper_id: mimitou_2021
title: "Scalable, multimodal profiling of chromatin accessibility, gene expression and protein levels in single cells."
doi: "10.1038/s41587-021-00927-2"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC8763625/"
source_ids: {doc_id: "pmc:8763625", pmid: "34083792", pmcid: "8763625", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "multi_cell_type_annotation", "atac_motif_analysis"]
retrieval_goals: ["prior_findings"]
retrieval_intents: ["Canonical PBMC cell type and subtype marker genes expected in human PBMC scRNA-seq and corresponding ATAC motif/peak signatures."]
extends: ["hao_2021", "cobolt_2021"]
added: 2026-05-15
session: unknown
---

## Summary
This paper introduces ASAP-seq, a scalable single-cell protocol that pairs scATAC-seq with oligo-conjugated antibody detection (via a bridge-oligo) to measure chromatin accessibility and hundreds of protein markers per cell, with optional mitochondrial DNA capture for clonal tracking; it also describes DOGMA-seq to jointly profile RNA and protein. The methods enable linked analyses of chromatin, transcript, and protein changes across hematopoietic differentiation, PBMC stimulation, and multiplexed T-cell perturbations, demonstrating compatibility with existing CITE-seq reagents and droplet-based platforms.

## Hypothesis framed
Antibody:oligonucleotide conjugates designed for single-cell RNA protein profiling can be repurposed for single-cell ATAC workflows (via a bridge oligo) to enable simultaneous, scalable measurement of chromatin accessibility and protein abundance (and optional mtDNA) in the same single cells.

## Questions answered
- Can antibody:oligonucleotide conjugates (CITE-seq reagents) be used in an scATAC-seq workflow to measure protein abundance concurrently with chromatin accessibility?
- Does fixation/permeabilization and transposition preserve antibody-derived protein signal and mitochondrial DNA for clonal tracking in a droplet-based scATAC workflow?
- Can multimodal joint profiling (chromatin + protein, and with DOGMA-seq: chromatin + RNA + protein) reveal coordinated and distinct regulatory changes during hematopoietic differentiation and immune stimulation?

## Key findings
ASAP-seq successfully measured chromatin accessibility and robustly detected hundreds of surface and intracellular protein markers in thousands of single cells; the bridge-oligo strategy allows use of existing commercial antibody:oligo panels while preserving sensitivity across a range of protein abundances despite modest fluorophore loss during transposition. Optional mtDNA capture enabled clonal tracking. Joint analyses with DOGMA-seq revealed modality-specific and coordinated changes across chromatin accessibility, RNA expression and surface protein during hematopoietic differentiation and PBMC stimulation, and the workflow is compatible with droplet-based platforms and CITE-seq reagents.

## Methods used
Adapted droplet-based mtscATAC-seq workflow; fixation and permeabilization of cells prior to transposition; bridge oligonucleotide strategy to link existing antibody:oligo conjugates to ATAC library sequences; flow cytometry to validate antibody signal retention; application to PBMCs, hematopoietic differentiation samples, stimulated and perturbed primary T cells; DOGMA-seq protocol to capture transcriptome plus protein; joint computational analyses linking ATAC peaks, RNA, protein, and mtDNA-derived clonality (including motif/peak analyses).

## Method and dataset
ASAP-seq: combines single-cell ATAC-seq with oligo-tagged antibodies (hundreds of proteins) and optional mtDNA capture on a droplet-based platform; applied to PBMCs, hematopoietic differentiation samples, and multiplexed/ stimulated primary T cells with experiments producing data from thousands of single cells per application and panels of hundreds of markers. Assumes cells tolerate fixation/permeabilization, that antibody:oligo reagents are available or compatible via a bridge oligo, and accepts typical single-cell ATAC sparsity per cell.

## Limitations
Inherits scATAC-seq sparsity (limited per-cell accessibility coverage); fixation/permeabilization and transposition can modestly reduce epitope signal and may not preserve all antigens equally; depends on availability and compatibility of antibody:oligo conjugates (requires bridge-oligo workaround for some reagents); DOGMA-seq is required to capture full transcriptomes which increases protocol complexity; integration and interpretation of sparse multimodal data require specialized computational methods.

## Evidence pattern
entity_definition, validation (flow cytometry and comparisons), statistical_unit (single cells, thousands), comparison_design (paired modality measurements across conditions), metric (protein counts, ATAC peak accessibility, mtDNA reads), covariates (stimulation/perturbation, differentiation state), analysis used (joint multimodal integration, motif/peak analysis, clonal tracking).

## Extends or contradicts
Extends prior single-cell protein-RNA pairing methods (CITE-seq) and mtDNA-retaining scATAC protocols (mtscATAC-seq) by enabling direct protein measurement in scATAC workflows via a bridge oligo and by combining chromatin, RNA and protein modalities (DOGMA-seq); complements multimodal integration methods (e.g., hao_2021, cobolt_2021) rather than contradicting them.

## Boundary conditions
Works when: Works when droplet-based scATAC platforms are used with cells that tolerate fixation/permeabilization, when antibody:oligo conjugates (or compatible reagents) are available for targeted proteins, when per-experiment cell counts are on the order of >= ~1,000 cells, and when targets include moderate-to-high abundance surface or intracellular proteins; mtDNA clonality capture works when mitochondria are retained through fixation/permeabilization.
Fails when: Fails or underperforms when target antigens are lost or heavily altered by fixation/permeabilization or transposition, when antibody:oligo reagents are unavailable or incompatible and bridge oligo cannot rescue them, when per-cell ATAC coverage is extremely low (exacerbating sparsity) or when experiments have very small cell numbers (< ~500 cells) limiting multimodal integration and downstream statistical power.
