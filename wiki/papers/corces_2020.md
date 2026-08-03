---
paper_id: corces_2020
title: "Single-cell epigenomic analyses implicate candidate causal variants at inherited risk loci for Alzheimer's and Parkinson's diseases."
doi: "10.1038/s41588-020-00721-x"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC7606627/"
source_ids: {doc_id: "pmc:7606627", pmid: "33106633", pmcid: "7606627", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_peak_to_gene", "multiomic_integration", "atac_motif_analysis"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Find computational strategies for connecting noncoding AD GWAS risk variants to cell-type-specific scATAC peaks, genes, and regulatory programs."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study generated a multi-omic epigenetic atlas of adult human brain using bulk ATAC-seq, single-cell ATAC-seq, chromatin interaction data, QTL data, and AD/PD GWAS summary statistics. It prioritized likely functional noncoding variants, linked them to putative target genes and brain cell types, and used a machine-learning classifier to predict regulatory effects on transcription-factor binding.

## Hypothesis framed
Inherited noncoding risk variants for Alzheimer's disease and Parkinson's disease can be prioritized as likely functional by integrating cell-type-specific adult human brain chromatin accessibility, chromatin contacts or co-accessibility, QTL evidence, GWAS association, and predicted transcription-factor-binding disruption.

## Questions answered
- Can AD and PD GWAS risk variants be linked to cell-type-specific accessible chromatin peaks and putative target genes in adult human brain?
- Which noncoding SNPs at AD and PD loci are predicted to have regulatory effects on transcription-factor binding?
- Does the MAPT Parkinson's disease risk haplotype show candidate ectopic neuronal regulatory interactions that could explain its disease association?

## Key findings
The study identified 186,559 reproducible bulk ATAC-seq peaks and generated single-cell chromatin accessibility profiles from 70,631 adult human brain cells. The integrative framework nominated dozens of candidate functional SNPs for Alzheimer's and Parkinson's disease loci, assigned putative target genes and relevant cell types to previously unresolved GWAS loci, supported known disease-relevant genes such as BIN1 in AD, suggested STAB1 as a PD-associated candidate, and identified candidate ectopic neuronal regulatory interactions at the MAPT inversion haplotype.

## Methods used
Bulk ATAC-seq across seven adult human brain regions; single-cell ATAC-seq across cortex, striatum, hippocampus, substantia nigra, and other disease-relevant regions; cell-type-specific accessible peak identification; integration with chromatin interaction datasets, co-accessibility networks, GTEx v8 QTLs, and AD/PD GWAS summary statistics; tiered SNP prioritization by peak overlap, target-gene linkage, and predicted regulatory effect; machine-learning prediction of SNP effects on transcription-factor binding; MAPT locus haplotype analysis.

## Method and dataset
The method was applied to adult human post-mortem brain tissue from cognitively healthy donors, including bulk ATAC-seq from seven brain regions and single-cell ATAC-seq from 70,631 cells, producing 186,559 reproducible bulk accessible chromatin peaks. The design integrated epigenomic maps with 3D chromatin contacts, co-accessibility, GTEx v8 QTLs, and AD/PD GWAS loci. The approach assumes that causal noncoding GWAS variants often act through accessible regulatory elements in relevant adult brain cell types, that target genes can be inferred from chromatin contacts, co-accessibility, or QTL links, and that sequence-level models can predict transcription-factor-binding disruption.

## Limitations
Most nominated variant-gene-cell-type assignments are computational predictions and require functional validation. Regulatory maps came from cognitively healthy post-mortem adult brain rather than AD or PD disease-state tissue. Some GWAS cohorts were not mutually exclusive. Cell-type and brain-region coverage was broad but not exhaustive. 3D chromatin interaction data were available only for selected cell types or datasets. The study does not directly prove causality for most nominated variants.

## Evidence pattern
The paper used entity definition by defining accessible regulatory peaks, candidate functional SNPs, putative target genes, and disease-relevant cell types; comparison design by contrasting accessibility across brain regions and cell types; statistical units including ATAC-seq peaks, SNPs, loci, genes, cell types, and individual cells; effect evidence from GWAS association, peak overlap, chromatin contacts, co-accessibility, QTL links, and predicted transcription-factor-binding disruption; validation and prioritization through convergence of multiple genomic annotations; and boundary conditions restricted to inherited noncoding regulatory variation in adult human brain contexts represented by the atlas.

## Extends or contradicts
This paper extends GWAS interpretation work by adding single-cell adult human brain chromatin accessibility and chromatin-contact-based variant-to-gene mapping for AD and PD loci; no direct contradiction of an existing listed wiki paper is indicated.

## Boundary conditions
Works when: Works best for inherited noncoding AD or PD GWAS loci where candidate variants or linked variants overlap accessible chromatin in profiled adult human brain regions or cell types, and where chromatin-contact, co-accessibility, or QTL evidence is available to assign putative target genes.
Fails when: Less reliable for variants acting only in unprofiled brain regions, rare or missing cell types, developmental stages, disease-state-specific regulatory programs, environmental or acquired disease mechanisms, coding variants, loci without usable LD or GWAS resolution, and loci lacking chromatin-contact, co-accessibility, or QTL support.
