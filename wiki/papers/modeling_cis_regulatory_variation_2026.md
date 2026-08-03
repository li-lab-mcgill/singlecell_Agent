---
paper_id: modeling_cis_regulatory_variation_2026
title: "Modeling cis -regulatory variation in human brain enhancers across a large Parkinson's Disease cohort."
doi: "10.64898/2026.03.15.711881"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC13015329/"
source_ids: {doc_id: "pmc:13015329", pmid: "41889906", pmcid: "13015329", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_peak_to_gene", "atac_motif_analysis", "multiomic_integration"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Find computational strategies for connecting noncoding AD GWAS risk variants to cell-type-specific scATAC peaks, genes, and regulatory programs."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study generated matched long-read whole-genome sequencing, DNA methylation, Fiber-seq, snATAC-seq, and snRNA-seq data from 190 human postmortem brain donors across anterior cingulate cortex and substantia nigra to model cis-regulatory variation in Parkinson's disease. It integrates caQTL, meQTL, allele-specific chromatin accessibility, sequence-to-function modeling, explainability, eQTL mapping, and locus modeling to identify enhancer variants, infer transcription factor disruption, connect variants to target genes, and prioritize functional noncoding PD GWAS variants.

## Hypothesis framed
Cell type-aware integration of chromatin accessibility QTLs, methylation QTLs, allele-specific chromatin accessibility, sequence-to-function models, and eQTL/locus modeling can identify cis-acting noncoding variants that alter human brain enhancer activity, explain their transcription factor mechanisms, and prioritize functional variants at Parkinson's disease GWAS loci.

## Questions answered
- Can matched long-read WGS and single-nucleus multiome data identify high-confidence cis-acting variants that modulate cell type-specific enhancer accessibility in human anterior cingulate cortex and substantia nigra?
- Can sequence-to-function models predict enhancer variant effects directly from genomic sequence and identify the disrupted transcription factor binding mechanisms?
- Can enhancer variant integration with eQTL mapping and locus-level modeling prioritize likely functional noncoding variants and target genes at Parkinson's disease GWAS loci, including in underpowered cell types such as dopaminergic neurons?

## Key findings
The study identified 53,841 high-confidence cis-acting genetic variants that modulate enhancer accessibility in a cell type-specific manner in one or both analyzed brain regions. caQTL and allele-specific chromatin accessibility signals were highly concordant, and increased chromatin accessibility was strongly associated with hypomethylation. Sequence-to-function models accurately predicted many enhancer variant effects from DNA sequence, explainability analyses indicated that most enhancer variants disrupt specific transcription factor binding sites in a cell type-specific manner, and integration with eQTL and locus modeling linked a subset of enhancer variants to likely target genes and prioritized candidate regulatory variants at known Parkinson's disease GWAS loci.

## Methods used
Oxford Nanopore long-read whole-genome sequencing, native DNA methylation profiling, Fiber-seq chromatin measurements, single-nucleus ATAC-seq, single-nucleus RNA-seq, chromatin accessibility QTL mapping, DNA methylation QTL mapping, allele-specific chromatin accessibility analysis, sequence-to-function modeling of variant effects, model explainability for transcription factor binding disruption, eQTL mapping, gene locus modeling, and integration with Parkinson's disease GWAS loci.

## Method and dataset
Matched multiomic postmortem brain dataset from 190 human donors, including 115 controls and 75 Parkinson's disease cases, sampled from anterior cingulate cortex and substantia nigra. Data included long-read WGS, native methylation, Fiber-seq, snATAC-seq from approximately 3.1 million nuclei, and snRNA-seq from approximately 1.1 million nuclei. The analysis assumes that cis associations between genotype and accessibility, methylation, allele-specific accessibility, and expression can identify regulatory variants; that sequence models trained or applied to genomic context can predict enhancer effects; and that eQTL/locus modeling can nominate variant-to-gene links when direct perturbation data are unavailable.

## Limitations
The cohort was predominantly of European ancestry, limiting generalizability to other populations. Postmortem brain samples vary in age, disease stage, postmortem interval, and biobank source, which may introduce confounding despite modeling controls. The sample size remains limited for rare variants, subtle disease-specific effects, and rare cell types such as dopaminergic neurons. Some enhancer variant-to-gene links are statistical or model-based and require experimental validation. The data are limited to anterior cingulate cortex and substantia nigra and may not capture regulatory effects in other Parkinson's disease-relevant tissues, developmental stages, or environmental contexts.

## Evidence pattern
Entity definition: enhancer variants were defined as cis-acting genetic variants supported by caQTL, meQTL, and/or allele-specific chromatin accessibility evidence that modulate enhancer accessibility. Statistical unit: donors, nuclei, cell types, brain regions, variants, chromatin accessibility peaks, methylation sites, and genes. Effect metrics: genotype-accessibility associations, genotype-methylation associations, allele-specific accessibility imbalance, sequence model-predicted variant effects, transcription factor binding disruption scores, eQTL associations, and locus-level variant-gene prioritization. Validation: concordance between caQTL and allele-specific chromatin accessibility, association of increased accessibility with hypomethylation, and agreement between sequence-to-function predictions and observed regulatory effects. Boundary conditions: analyses were performed in postmortem anterior cingulate cortex and substantia nigra from 190 donors enriched for European ancestry.

## Extends or contradicts
Extends single-cell chromatin and multiomic cis-regulatory mapping approaches by combining caQTL, meQTL, allele-specific accessibility, sequence-to-function modeling, explainability, eQTL integration, and locus modeling in a large matched human brain Parkinson's disease cohort. No direct contradiction of prior findings is reported in the summary.

## Boundary conditions
Works when: Applies to matched genotype and brain single-nucleus multiome datasets with enough donors for cis-QTL mapping, enough nuclei to resolve major brain cell types, measurable chromatin accessibility and RNA expression, and GWAS loci in noncoding regulatory regions. The framework is especially useful when caQTL/ASCA/meQTL signals and sequence-to-function predictions can be integrated to prioritize variants in cell types where direct QTL mapping has limited power.
Fails when: May fail or be underpowered for rare variants, very rare cell types with few nuclei, subtle disease-specific regulatory effects, non-European populations not represented in the cohort, brain regions or developmental contexts not sampled, and variant-to-gene links that require experimental perturbation rather than statistical or model-based inference.
