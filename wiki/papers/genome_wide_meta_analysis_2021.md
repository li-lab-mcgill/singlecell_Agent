---
paper_id: genome_wide_meta_analysis_2021
title: "Genome-wide meta-analysis, fine-mapping and integrative prioritization implicate new Alzheimer's disease risk genes."
doi: "10.1038/s41588-020-00776-w"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC7610386/"
source_ids: {doc_id: "pmc:7610386", pmid: "33589840", pmcid: "7610386", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Find computational strategies for connecting noncoding AD GWAS risk variants to cell-type-specific scATAC peaks, genes, and regulatory programs, including validation and failure modes."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This paper performed an updated Alzheimer's disease genome-wide association meta-analysis, SNP-level fine-mapping, eQTL colocalization across 109 expression QTL datasets, and integrative gene prioritization using protein interaction networks and tissue-specific expression. It identified 37 AD risk loci taken forward for follow-up and prioritized likely causal genes including CCDC6, TSPAN14, NCK2, SPRED2, BIN1, APH1B, PTK2B, PILRA, and CASS4.

## Hypothesis framed
Alzheimer's disease GWAS loci can be resolved into more likely causal variants and genes by combining large-scale GWAS meta-analysis, SNP-level fine-mapping, eQTL colocalization, protein interaction evidence, and tissue-specific expression evidence.

## Questions answered
- Which Alzheimer's disease risk loci are detected by meta-analyzing UK Biobank AD-by-proxy data with the Kunkle et al. AD GWAS?
- Which SNPs at AD risk loci have greater than 50% posterior probability of being causally involved in AD risk under SNP-level fine-mapping?
- Which genes at AD GWAS loci are prioritized when fine-mapping, eQTL colocalization across 109 datasets, protein interaction networks, and tissue-specific expression are integrated into a quantitative score?

## Key findings
The UK Biobank analysis identified 13 genome-wide significant AD risk loci, including novel signals near NCK2, PRL, and FAM135B. Meta-analysis with the Kunkle et al. dataset identified 34 genome-wide significant loci, including four novel loci near NCK2, TSPAN14, SPRED2, and CCDC6; 37 loci including suggestive loci were followed up. Fine-mapping identified 21 SNPs with greater than 50% probability of being causally involved in AD risk. Integrative prioritization implicated CCDC6, TSPAN14, NCK2, SPRED2, BIN1, APH1B, PTK2B, PILRA, and CASS4; among the four novel meta-analysis loci, only TSPAN14 reached nominal replication in FinnGen.

## Methods used
Genome-wide association-by-proxy analysis in UK Biobank; meta-analysis with the Kunkle et al. AD GWAS; three SNP-level fine-mapping methods; functional annotation of variants; colocalization analyses across 109 gene expression quantitative trait locus datasets; gene prioritization using protein interaction networks and tissue-specific expression; quantitative integration of evidence streams into a gene prioritization score; replication checks including FinnGen.

## Method and dataset
The study analyzed UK Biobank participants of European ancestry, using diagnosed AD cases and proxy cases defined by family history of AD or dementia versus controls, then meta-analyzed these results with a prior large AD GWAS from Kunkle et al. The follow-up design evaluated 37 AD risk loci using SNP-level fine-mapping, eQTL colocalization across 109 expression QTL datasets, protein interaction networks, and tissue-specific expression. The integrative approach assumes that causal AD genes may be supported by convergence of genetic association, fine-mapped variant probability, regulatory colocalization, protein network connectivity, and disease-relevant tissue expression.

## Limitations
The UK Biobank component relied heavily on proxy AD cases based on family history of AD or dementia rather than clinically confirmed AD diagnoses, which may introduce phenotype misclassification. Analyses were restricted to individuals of European ancestry, limiting generalizability. Replication datasets had limited statistical power, particularly for novel loci. Colocalization evidence was sometimes observed in only one or a few expression datasets, so absence of colocalization does not reliably exclude a gene or tissue-specific mechanism. The study did not directly map variants to single-cell ATAC-seq peaks, cell-type-specific chromatin accessibility, peak-to-gene links, regulatory motifs, or experimentally validated enhancer effects.

## Evidence pattern
Entity definition: AD cases included diagnosed cases and proxy cases based on family history of AD or dementia; controls lacked those definitions. Comparison design: GWAS of cases/proxy cases versus controls followed by meta-analysis with an external AD GWAS. Statistical unit: SNPs for association and fine-mapping; genes for colocalization and prioritization. Metrics: genome-wide significant loci, posterior probability of causality greater than 50% for fine-mapped SNPs, colocalization evidence, and an integrated quantitative gene prioritization score. Validation: replication checks in external datasets including FinnGen. Boundary conditions: European-ancestry GWAS data, available eQTL resources, and probabilistic rather than experimental causal assignment.

## Extends or contradicts
Extends prior AD GWAS work, including the Kunkle et al. dataset, by adding UK Biobank AD-by-proxy association results, updated meta-analysis, fine-mapping, eQTL colocalization, and integrative gene prioritization. It does not directly extend or contradict any listed single-cell ATAC-seq or single-cell multiomic paper.

## Boundary conditions
Works when: Works when large European-ancestry GWAS summary statistics are available; when case-control or proxy-case definitions can be harmonized for meta-analysis; when loci have sufficient association signal for SNP-level fine-mapping; and when relevant eQTL, protein interaction, and tissue-specific expression datasets exist for candidate gene prioritization.
Fails when: Does not resolve mechanisms that require cell-type-specific chromatin accessibility, direct scATAC peak overlap, peak-to-gene linkage, motif analysis, or enhancer perturbation. Performance is limited when phenotypes are misclassified proxy AD labels, when non-European populations are analyzed without matching reference data, when replication cohorts are underpowered, or when causal regulation occurs in tissues or cell states absent from the eQTL datasets.
