---
paper_id: interrogation_human_hematopoiesis_2019
title: "Interrogation of human hematopoiesis at single-cell and single-variant resolution."
doi: "10.1038/s41588-019-0362-6"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC6441389/"
source_ids: {doc_id: "pmc:6441389", pmid: "30858613", pmcid: "6441389", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_cell_type_annotation"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Find the g-chromVAR methods paper for single-cell GWAS enrichment from scATAC peaks."]
extends: []
added: 2026-05-27
session: unknown
---

## Summary
This paper fine-maps UK Biobank blood trait GWAS loci and integrates posterior probabilities of causality with hematopoietic chromatin accessibility to localize regulatory mechanisms, target genes, and causal cell types. It introduces g-chromVAR, which combines fine-mapped variant probabilities with continuous chromatin accessibility to resolve trait enrichments among closely related populations and at single-cell resolution.

## Background
Linkage disequilibrium and incomplete annotation of dynamic hematopoietic states hinder identification of causal variants and mechanisms from GWAS. Blood traits are heritable, lineage-structured phenotypes that enable connecting genetic variation to regulatory programs and cell types across hematopoiesis.

## Method and dataset
GWAS of ~115,000 UK Biobank participants for 16 blood traits were fine-mapped across 2,056 significant regions using LD from imputed genotype dosages, allowing up to five causal variants per locus and assigning per-variant posterior probabilities (MAF > 0.1%, INFO > 0.6). Fine-mapped variants were integrated with ATAC-seq from 18 primary human hematopoietic populations and with single-cell ATAC-seq profiles to assess developmental enhancer activity, nominate molecular mechanisms, and identify likely target genes. The g-chromVAR method combines fine-mapped variant posterior probabilities with continuous chromatin accessibility to compute trait enrichments in closely related cell populations and in single cells; it assumes well-imputed common variants and accurate continuous accessibility quantification.

## Analysis
Fine-mapping produced per-variant posterior probabilities across GWAS loci; enrichment of fine-mapped variants was evaluated in pathways and in accessible chromatin from 18 hematopoietic populations. Trait–cell type enrichments were quantified using S-LDSC, GREGOR, GPA, and fGWAS with Bonferroni correction. Developmental enhancer activity and regulatory mechanisms were inferred for regulatory variants, and likely target genes were nominated. Pleiotropy patterns across traits were characterized by mapping variant effects to hematopoietic progenitors and lineages. g-chromVAR combined fine-mapped posterior probabilities with continuous chromatin accessibility to refine trait enrichment among closely related populations and to single cells from scATAC-seq.

## Key findings
Identified 38,654 variants with >1% posterior probability across associated regions; 48% of regions contained at least one variant with PP > 0.50. Fine-mapped variants collectively explained on average 24.9% of the narrow-sense heritability carried by common variants; mean trait heritability from common variants was ~15.4%. At PP > 0.10, 240 coding and 647 regulatory variants overlapped accessible chromatin in at least one of 18 hematopoietic populations, with enrichment in trait-relevant pathways and progenitor chromatin. Multiple independent variants frequently localized to the same regulatory element or gene, indicating allelic complexity. Regulatory variants showed stage-specific enhancer activity; high-confidence regulatory mechanisms were assigned for 145 variants, and experimentally supported target genes were identified for 79% of variants overlapping accessible chromatin. Pleiotropic variants predominantly acted in common progenitors to modulate overall blood production (~90%), with ~10% exhibiting lineage-switch effects. g-chromVAR enabled detection of trait–cell type enrichments within closely related populations and at single-cell resolution, refining causal cell-type assignment beyond bulk analyses.

## Limitations
Conclusions are largely correlative with limited experimental validation; rare or poorly imputed variants may be missed due to focus on common, well-imputed variants. Results are primarily from UK Biobank participants and may not generalize across ancestries. Single-cell resolution was limited to available hematopoietic scATAC-seq populations and may not capture all relevant states; LD structure and model assumptions can confound causal attribution in complex loci.

## Metrics used
Posterior probability of causality thresholds (>0.01, >0.10, >0.50); proportion of narrow-sense heritability explained (24.9%); mean trait heritability from common variants (~15.4%); counts of fine-mapped variants (38,654), coding (240) and regulatory (647) variants overlapping chromatin; fraction of regions with high-PP variants (48%); fraction of variants with experimentally supported target genes (79%); pleiotropy proportions (~90% progenitor-tuning vs ~10% lineage-switch); enrichment statistics from S-LDSC, GREGOR, GPA, and fGWAS with Bonferroni correction.
