---
paper_id: single_nucleus_epigenomic_2025
title: "Single-nucleus epigenomic dysregulation unmasks genetic risk-associated neurodegenerative glia states."
doi: "10.1101/2025.06.02.657512"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12157633/"
source_ids: {doc_id: "pmc:12157633", pmid: "40502140", pmcid: "12157633", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_differential_accessibility", "atac_peak_to_gene", "multiomic_integration"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Find computational strategies for connecting noncoding AD GWAS risk variants to cell-type-specific scATAC peaks, genes, and regulatory programs."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study used paired single-nucleus chromatin accessibility and gene expression profiling of postmortem brain tissue from Alzheimer's disease, Pick's disease, progressive supranuclear palsy, and controls to map disease-dynamic cis-regulatory elements across six major cell types and fifty subclasses. It matters because it provides a multi-omic strategy for linking noncoding neurodegenerative disease risk variants to cell-type-specific accessible chromatin, candidate genes, glial regulatory states, and pathways such as sphingomyelin regulation in Pick's disease.

## Hypothesis framed
Noncoding genetic risk variants for tau-related dementias alter cell-type- and disease-state-specific cis-regulatory elements, with glial regulatory programs mediating disorder-specific neurodegenerative risk and resilience.

## Questions answered
- Which neuronal and glial cell types show disease-dynamic chromatin accessibility changes across Alzheimer's disease, Pick's disease, and progressive supranuclear palsy?
- Are neurodegenerative disease GWAS risk signals enriched in disease-dynamic cis-regulatory elements in specific brain cell types?
- Can co-accessibility, eQTL, GWAS, and MPRA integration connect noncoding risk variants to glial regulatory modules, candidate target genes, and pathways?

## Key findings
After analyzing more than 680,000 nuclei from 41 individuals, the study identified disease- and cell-type-specific chromatin accessibility changes across neurons and glia. Glial cells overrepresented disorder-specific regulatory remodeling related to dynamic cellular stress responses; astrocytes and inhibitory neurons showed broad accessibility reductions in Pick's disease and progressive supranuclear palsy. Genetic risk signals were enriched in disease-dynamic regulatory elements in a cell-type-specific manner, with frontotemporal dementia-related heritability especially linked to dynamic microglial accessibility. Microglial regulatory variants converged into co-regulated functional modules, and polygenic risk modifiers were most co-accessible in disorder-specific glial states, including Pick's disease glial programs implicating sphingomyelin regulation.

## Methods used
Single-nucleus ATAC-seq of postmortem brain tissue; matched in-house single-nucleus RNA-seq integration; major cell type and subclass annotation; identification of cell-type-specific accessible chromatin peaks; transcription factor motif analysis; disease-dynamic cis-regulatory element analysis across disorders and regions; integration with GWAS loci, single-cell eQTLs, co-accessibility, and MPRA functional variant datasets to prioritize variant-peak-gene links, regulatory modules, and pathways.

## Method and dataset
The analysis used single-nucleus ATAC-seq from postmortem brain tissue from 41 individuals including controls and Alzheimer's disease, Pick's disease, and progressive supranuclear palsy cases across multiple brain regions, with more than 680,000 nuclei after quality control, integrated with matched in-house single-nucleus RNA-seq. The experimental design compared controls and three tau-related dementias across brain cell types and subclasses, with downstream analyses mainly focused on the insula and precentral gyrus because of regional sampling constraints. The computational strategy assumes that accessible chromatin peaks mark candidate cis-regulatory elements, disease-associated accessibility changes reflect disease-relevant regulatory states, and co-accessibility plus eQTL, GWAS, and MPRA evidence can nominate likely variant-to-gene regulatory links.

## Limitations
The study used postmortem tissue and is observational, limiting causal interpretation of regulatory changes. The cohort size was modest at 41 individuals, and some brain regions had limited or variable sampling, causing downstream analyses to focus mainly on the insula and precentral gyrus. Regional tissue dissection differences and cell composition differences may confound disease comparisons. Variant-to-gene and regulatory-module assignments depend on computational integration of chromatin accessibility, eQTL, GWAS, and MPRA datasets and need experimental validation in relevant human brain cell types. The study may not capture temporal disease progression, early pathogenic regulatory events, all tauopathy subtypes, or ancestry-specific genetic effects.

## Evidence pattern
Entity definition: cell-type-specific cis-regulatory elements were defined from snATAC-seq peaks across six major cell types and fifty subclasses. Comparison design: chromatin accessibility and regulatory programs were compared across controls and Alzheimer's disease, Pick's disease, and progressive supranuclear palsy, including disorder- and region-aware analyses. Statistical unit: single nuclei aggregated into annotated cell types/subclasses and disease groups from 41 individuals. Analysis used: differential accessibility, motif enrichment, snATAC-snRNA integration, co-accessibility, GWAS heritability/enrichment analyses, single-cell eQTL integration, and MPRA functional variant integration. Validation: external functional variant data from MPRA assays and eQTL evidence were used to support prioritized regulatory links. Boundary conditions: conclusions are based on postmortem human brain nuclei and strongest downstream analyses in insula and precentral gyrus.

## Extends or contradicts
This extends prior single-cell neurodegeneration and cis-regulatory mapping work by applying paired single-nucleus chromatin accessibility and gene expression profiling across three tau-related dementias and explicitly integrating disease-dynamic CREs with GWAS, eQTL, co-accessibility, and MPRA evidence to prioritize glial variant-to-gene regulatory programs. No direct contradiction of a listed prior wiki paper is specified in the summary.

## Boundary conditions
Works when: The strategy applies when single-nucleus ATAC-seq data have enough nuclei to resolve major brain cell types and subclasses, matched or compatible snRNA-seq is available for annotation and gene-expression context, disease and control samples can be compared within relevant brain regions, and external GWAS, fine-mapping, eQTL, or MPRA resources exist for the variants being interpreted.
Fails when: The approach is weak when sample size or regional coverage is too limited for disease-by-cell-type comparisons, when postmortem or tissue-dissection artifacts dominate accessibility differences, when cell composition differences are not controlled, when ancestry mismatch limits GWAS transferability, or when inferred co-accessibility/eQTL/MPRA links are treated as causal without perturbational validation.
