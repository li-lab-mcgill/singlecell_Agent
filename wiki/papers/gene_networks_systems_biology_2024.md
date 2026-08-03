---
paper_id: gene_networks_systems_biology_2024
title: "Gene networks and systems biology in Alzheimer's disease: Insights from multi-omics approaches."
doi: "10.1002/alz.13790"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC11095483/"
source_ids: {doc_id: "pmc:11095483", pmid: "38534018", pmcid: "11095483", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "multi_grn_inference", "atac_grn_inference"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["Learn what prior single-cell or chromatin studies show about AD-associated cis-regulatory elements, enhancer-target gene links, TF programs, and non-coding AD risk localization by brain cell type."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This review summarizes how bulk transcriptomics, single-cell and single-nucleus RNA-seq, single-nucleus ATAC-seq, epigenomic profiling, spatial omics, and gene regulatory network analysis have been used to study Alzheimer's disease. It matters for AD regulatory genomics because it frames noncoding AD risk variants as candidates for interpretation through cell-type-specific chromatin accessibility, especially in microglia.

## Hypothesis framed
Integrating transcriptomic, epigenomic, spatial, and gene regulatory network data provides a more complete explanation of Alzheimer's disease biology than single-modality analyses, particularly for connecting noncoding genetic risk to cell-type-specific regulatory mechanisms.

## Questions answered
- Do Alzheimer's disease-associated noncoding variants localize to cell-type-specific accessible chromatin in brain cells?
- Which brain cell type is most consistently implicated by single-cell epigenomic enrichment of AD risk SNPs?
- Can ATAC-seq alone identify downstream target genes for AD-associated accessible loci?

## Key findings
The review concludes that multi-omics studies support cell-type-specific mechanisms in Alzheimer's disease, with microglia highlighted as a major implicated cell type. It reports that snATAC-seq studies found AD-associated SNPs enriched in microglia-specific accessible chromatin regions, supporting a role for microglial immune and regulatory mechanisms in AD risk and pathogenesis. It also concludes that ATAC-seq identifies accessible loci but does not by itself establish downstream enhancer-target genes.

## Methods used
Narrative review of published Alzheimer's disease studies using bulk transcriptomics, single-cell RNA-seq, single-nucleus RNA-seq, single-nucleus ATAC-seq, epigenomic profiling, spatial omics, and gene regulatory network analysis.

## Method and dataset
Review article synthesizing previously published bulk, single-cell, single-nucleus, epigenomic, spatial, and network-based Alzheimer's disease datasets. No primary dataset size, sample count, cell count, or experimental design is specified in the summary.

## Limitations
The review does not provide primary single-nucleus multiome data, quantitative cell-type-specific enrichment statistics for AD GWAS loci, direct enhancer-target gene links, detailed TF motif or regulon programs by brain cell type, specific evidence for APOE, CLU, or SREBF1 regulatory loci, or prefrontal cortex-specific chromatin accessibility results. snRNA-seq can identify altered expression but not the regulatory mechanisms driving it; ATAC-seq can identify accessible loci but not downstream target genes by itself.

## Evidence pattern
Entity definition and boundary-condition evidence from a narrative review. The paper defines AD-associated noncoding risk interpretation in terms of regulatory elements such as promoters, enhancers, and cell-type-specific accessible chromatin; it cites prior snATAC-seq evidence that AD risk SNPs are enriched in microglia-accessible regions. There is no primary statistical unit, no reported enrichment metric, no covariate model, and no primary validation described in the summary.

## Extends or contradicts
Extends the general single-cell and epigenomic AD literature by synthesizing how transcriptomic, chromatin accessibility, spatial, and gene regulatory network approaches can be combined to interpret AD risk and disease mechanisms. No contradiction of a specific prior wiki paper is described.

## Boundary conditions
Works when: Applicable as background evidence when the research question concerns Alzheimer's disease, noncoding GWAS variants, cell-type-specific chromatin accessibility, microglia-accessible regulatory regions, or the need to integrate transcriptomic, epigenomic, spatial, and regulatory network data.
Fails when: Not sufficient when the task requires primary multiome measurements, quantitative enrichment statistics, causal enhancer-target gene assignment, locus-specific regulatory evidence for APOE, CLU, or SREBF1, detailed TF motif or regulon programs, or prefrontal cortex-specific chromatin accessibility results.
