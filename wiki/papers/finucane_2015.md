---
paper_id: finucane_2015
title: "Partitioning heritability by functional annotation using genome-wide association summary statistics."
doi: "10.1038/ng.3404"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC4626285/"
source_ids: {doc_id: "pmc:4626285", pmid: "26414678", pmcid: "4626285", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: []
retrieval_goals: ["method_selection"]
retrieval_intents: ["canonical reference for stratified LD score regression (S-LDSC)", "guidance on joint conditional modeling across overlapping annotations", "control for annotation size and overlap in heritability partitioning", "cautions against unadjusted enrichment analyses using summary statistics"]
extends: []
added: 2026-05-27
session: unknown
---

## Summary
Introduces stratified LD score regression (S-LDSC) to partition SNP-heritability across overlapping functional annotations and cell type–specific elements using only GWAS summary statistics while accounting for LD. Applied to 17 complex traits (average N=73,599), it identifies strong enrichment in conserved regions, immunological disease-specific enrichment in FANTOM5 enhancers, and CNS-related enrichments for several behavioral and reproductive traits.

## Background
Functional genomic categories contribute unequally to complex trait heritability, but many prior approaches require individual-level data, ignore LD, assume a single causal variant per locus, or rely only on significant loci. A summary-statistics–based, LD-aware method was needed to quantify annotation-specific heritability and enrichment across overlapping annotations and detect trait- and cell type–specific signals even when few genome-wide significant loci exist.

## Method and dataset
S-LDSC regresses GWAS SNP-level chi-square statistics on stratified LD scores computed per functional annotation to estimate each annotation’s contribution to SNP-heritability while jointly controlling for all annotations in a baseline model. The study used a 53-annotation baseline model, additional cell type–specific annotations and groups, and LD scores computed from 1000 Genomes European reference genotypes; analyses covered 17 traits with average sample size 73,599. Assumptions include additive effects, correct population-matched LD reference, and that summary statistics capture polygenic signal.

## Analysis
1) Constructed a joint baseline model of 53 overlapping functional categories plus cell type–specific annotations and grouped cell types (e.g., CNS). 2) Computed stratified LD scores per SNP and annotation using 1000 Genomes Europeans. 3) Performed joint regression of GWAS chi-square statistics on stratified LD scores to estimate per-annotation heritability contributions, enrichment (proportion h2 divided by proportion of SNPs), and statistical significance. 4) Simulations (N=14,000; h2=0.7; p_causal=0.05 or 0.005) with realistic and null enrichment scenarios assessed calibration, power, and top-ranked causal group/type recovery. 5) Benchmarked against GoShifter, fgwas, a top-SNPs enrichment test, PICS, and an unadjusted S-LDSC variant to evaluate type I error and power.

## Benchmark methods
GoShifter; fgwas; top SNPs enrichment test (Maurano-like); PICS; unadjusted stratified LD score regression

## Key findings
S-LDSC robustly partitions SNP-heritability across overlapping annotations using summary statistics and LD, revealing broad enrichment in conserved regions across many traits; very large, immunological disease-specific enrichment in FANTOM5 enhancers; and significant CNS group enrichment for body mass index, age at menarche, educational attainment, and smoking behavior. In simulations with realistic enrichment, the true causal cell-type group was top in 99% of significant runs; under weaker enrichment, it was top in 95% of significant runs, with remaining tops largely from highly correlated groups (r2>0.5). At the individual cell-type level under realistic enrichment, the causal type was top in 78% of significant runs, with r2>0.5 correlates top in 20%. S-LDSC showed higher power than GoShifter in more polygenic scenarios and comparable power in less polygenic ones; fgwas had good null calibration but lower power than S-LDSC across tested settings. Top-SNP and PICS analyses exhibited inflated false positives under null baseline enrichment, mirroring unadjusted S-LDSC that does not control for other annotations.

## Limitations
Requires large GWAS sample sizes and/or substantial SNP-heritability and polygenicity; depends on population-matched LD reference (limited here to Europeans); not applicable to custom arrays like Metabochip; assumes additive genetic effects and ignores epistasis; cannot assess variants absent from the reference (e.g., extremely rare variants); results depend on the quality and completeness of functional annotations.

## Metrics used
Annotation-specific proportion of SNP-heritability; enrichment (proportion of h2 divided by proportion of SNPs in annotation); P-values for enrichment; simulation rejection rates (power and type I error); identity of top-ranked causal group/cell type; calibration under null scenarios.

## Figure captions
Figures detail the S-LDSC joint regression across a 53-annotation baseline model, definition of enrichment metrics, demonstrations that unadjusted analyses are misleading when annotations overlap, simulations validating calibration and power, and benchmarking versus GoShifter, fgwas, top-SNPs, PICS—providing core guidance for conditional/joint modeling and overlap control.