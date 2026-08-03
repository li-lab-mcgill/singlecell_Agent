---
paper_id: epigenomic_dissection_ad_2023
title: "Epigenomic dissection of Alzheimer's disease pinpoints causal variants and reveals epigenome erosion."
doi: "10.1016/j.cell.2023.08.040"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC10782612/"
source_ids: {doc_id: "pmc:10782612", pmid: "37774680", pmcid: "10782612", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "atac_peak_to_gene", "atac_grn_inference"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Find computational strategies for connecting noncoding AD GWAS risk variants to cell-type-specific scATAC peaks, genes, and regulatory programs, including validation and failure modes."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study profiled single-nucleus RNA-seq, single-nucleus ATAC-seq, and multiome data from postmortem prefrontal cortex of 92 individuals with non-AD, early-stage AD, or late-stage AD, totaling about 850,000 nuclei. It integrated cell-type-specific chromatin accessibility, gene expression, peak-to-gene links, co-accessibility modules, transcription factor programs, ATAC-QTLs, and AD GWAS loci to prioritize regulatory circuits for non-coding AD risk variants.

## Hypothesis framed
Non-coding AD risk variants exert effects through cell-type-specific regulatory elements and enhancer-to-gene circuits in human brain cell types, and AD progression is accompanied by stage- and cell-type-specific chromatin accessibility changes culminating in late-stage epigenome erosion.

## Questions answered
- Which human prefrontal cortex cell types and regulatory elements are enriched for non-coding AD GWAS risk loci?
- Can cell-type-specific peak-to-gene links and ATAC-QTLs prioritize candidate causal AD variants, target genes, transcription factors, and regulatory circuits?
- How does chromatin accessibility of regulatory modules change between non-AD, early-stage AD, and late-stage AD brains?

## Key findings
AD risk loci were enriched in microglial enhancers and in regulatory programs or binding sites involving SPI1, ELF2, and RUNX1. The study identified 9,628 cell-type-specific ATAC-QTL loci and used these with peak-to-gene links to nominate AD variant regulatory circuits. Regulatory module accessibility changes were prominent in glia in late-stage AD and detectable in neurons in early-stage AD, while late-stage AD showed broad epigenomic dysregulation consistent with epigenome erosion and partial cell identity loss.

## Methods used
Single-nucleus RNA-seq, single-nucleus ATAC-seq, and multiome profiling of postmortem prefrontal cortex; cell type and subtype annotation; identification of cell-type-specific accessible chromatin peaks; multimodal RNA-ATAC integration; peak-to-gene linking; co-accessibility module and regulatory module detection; transcription factor motif/regulator analysis; differential chromatin accessibility analysis across AD stages; ATAC-QTL mapping; integration of AD GWAS loci with enhancers, ATAC-QTLs, transcription factors, and peak-to-gene links.

## Method and dataset
The analysis used transcriptomic and chromatin accessibility profiles from more than 800,000 single nuclei from prefrontal cortex samples of 92 Religious Order Study and Rush Memory and Aging Project participants classified as non-AD, early-stage AD, or late-stage AD. The method links non-coding variants to genes by combining cell-type-specific ATAC peaks, peak-to-gene relationships inferred from multimodal accessibility-expression patterns, co-accessibility/regulatory modules, ATAC-QTLs, and AD GWAS loci. The approach assumes that enhancer accessibility, co-accessibility, peak-gene correlation, and local genetic effects on chromatin accessibility provide evidence for regulatory relationships, and that postmortem single-nucleus profiles preserve disease-relevant cell-type-specific regulatory states.

## Limitations
The study used postmortem tissue, so regulatory changes may reflect disease consequences, agonal effects, or tissue preservation artifacts rather than initiating AD causes. It focused on prefrontal cortex, limiting inference to other AD-relevant brain regions. Late-stage AD sample size was modest, and low-abundance cell populations such as vascular cells had reduced power. Variant prioritization and enhancer-to-gene assignments are computational and require direct experimental perturbation validation. Sparse single-nucleus assays may miss low-abundance transcripts or regulatory events.

## Evidence pattern
The paper supports its claims by defining cell types, accessible peaks, regulatory modules, ATAC-QTLs, and peak-to-gene links as analysis entities; comparing non-AD, early-stage AD, and late-stage AD individuals; using nuclei nested within 92 donors as the profiling units while deriving disease-stage and genetic associations at donor or cell-type-specific levels; measuring chromatin accessibility, gene expression, GWAS enrichment, TF motif/regulatory enrichment, peak-to-gene linkage, co-accessibility, and ATAC-QTL association. Evidence comes from multimodal integration, disease-stage differential accessibility, enrichment of AD GWAS loci in cell-type-specific enhancers, and computational triangulation of GWAS variants with ATAC-QTLs and peak-to-gene links rather than direct perturbational validation.

## Extends or contradicts
This extends prior AD GWAS findings by assigning non-coding risk loci to human brain cell-type-specific enhancers, candidate target genes, transcription factors, and regulatory circuits; it does not directly contradict a named prior paper in the provided summary.

## Boundary conditions
Works when: Applicable to large multi-donor single-nucleus RNA-seq, single-nucleus ATAC-seq, or multiome datasets with enough nuclei per cell type to call cell-type-specific peaks, infer peak-to-gene links, detect co-accessibility modules, and map chromatin QTLs. Most directly supported for postmortem human prefrontal cortex samples with donor metadata for AD stage and genotype, especially abundant brain cell classes such as neurons, microglia, astrocytes, oligodendrocytes, and other major glial populations.
Fails when: Less reliable for rare cell populations with low nuclei counts, cohorts with too few genotyped donors for ATAC-QTL mapping, datasets lacking matched or integrable RNA and ATAC information for peak-to-gene inference, brain regions outside prefrontal cortex without replication, and causal claims requiring separation of inherited AD risk mechanisms from downstream disease-stage or postmortem chromatin changes.
