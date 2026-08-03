---
paper_id: integration_alzheimers_disease_2021
title: "Integration of Alzheimer's disease genetics and myeloid genomics identifies disease risk regulatory elements and genes."
doi: "10.1038/s41467-021-21823-y"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC7955030/"
source_ids: {doc_id: "pmc:7955030", pmid: "33712570", pmcid: "7955030", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "atac_peak_to_gene", "atac_motif_analysis"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["Learn what prior single-cell or chromatin studies show about AD-associated cis-regulatory elements, enhancer-target gene links, TF programs, and non-coding AD risk localization by brain cell type."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study integrated Alzheimer's disease GWAS with human myeloid epigenomic and transcriptomic datasets from monocytes, macrophages, and microglia to identify disease-associated regulatory elements, candidate functional variants, and likely target genes. It found that AD heritability is enriched specifically in active myeloid enhancers and nominated AD risk enhancers and target genes in 20 loci, with experimental validation of a regulatory variant at the MS4A locus.

## Hypothesis framed
Alzheimer's disease non-coding risk alleles are preferentially localized in active enhancers of myeloid cells, including monocytes, macrophages, and microglia, where they modify disease risk by altering enhancer activity and target gene expression.

## Questions answered
- Are AD GWAS risk alleles enriched in active enhancers of monocytes, macrophages, and microglia rather than in other regulatory annotations?
- Which myeloid cis-regulatory elements and enhancer-linked genes are implicated at AD risk loci?
- Can fine-mapping identify candidate functional non-coding variants at AD loci, and can one such variant be experimentally validated in microglia-relevant systems?

## Key findings
AD risk alleles were specifically enriched in active enhancers of monocytes, macrophages, and microglia. These AD risk enhancers were enriched for myeloid transcription factor motifs including PU.1, AP-1, C/EBP, CTCF, RUNX, and microglia-enriched MEF2 motifs. The study nominated AD risk enhancers and likely target genes in 20 AD loci, including AP4E1, AP4M1, APBB3, BIN1, MS4A4A, MS4A6A, PILRA, RABEP1, SPI1, TP53INP1, and ZYX. Fine-mapping prioritized candidate functional variants predicted to alter myeloid gene regulation, and at the MS4A locus the authors narrowed the signal to a single candidate functional variant and validated its regulatory effect in hiPSC-derived microglia and human brain data.

## Methods used
Human ChIP-seq and ATAC-seq datasets from monocytes, macrophages, and microglia were processed to define active enhancers, active promoters, primed enhancers, and primed promoters using H3K27ac, H3K4me1, H3K4me2, H3K4me3, and open chromatin. Stratified LD score regression was used to test enrichment of AD SNP heritability in myeloid annotations, with schizophrenia used as a control trait. The authors integrated enhancer annotations with open chromatin, transcription factor motif analysis, expression quantitative trait loci, enhancer-promoter linking, transcriptomic data, and fine-mapping to nominate regulatory variants and target genes. A candidate MS4A functional variant was validated using human induced pluripotent stem cell-derived microglia and human brain data.

## Method and dataset
The analysis used AD GWAS summary statistics covering more than 40 AD-associated loci together with bulk myeloid epigenomic datasets, including ChIP-seq for H3K27ac, H3K4me1, H3K4me2, and H3K4me3, ATAC-seq/open chromatin data, eQTL resources, enhancer-promoter links, and transcriptomic data from human monocytes, macrophages, and microglia. Exact sample counts are not provided in the summary. The design assumes that active enhancer annotations in available myeloid datasets capture regulatory elements relevant to AD genetic risk, that LD score regression enrichment reflects disease-relevant localization of heritability, and that enhancer-promoter links and eQTLs can nominate likely target genes for non-coding risk variants.

## Limitations
Most nominated variants, enhancers, and target genes outside the MS4A locus remain computational predictions. The epigenomic datasets may not capture all microglial states, disease stages, brain regions, ancestry groups, or environmental contexts relevant to Alzheimer's disease. Enhancer-gene linking remains uncertain for distal regulatory elements. The study focuses on myeloid cells and has limited coverage of non-myeloid brain cell types such as neurons, astrocytes, oligodendrocytes, and endothelial cells. It is not primarily a single-cell atlas of AD brain chromatin states.

## Evidence pattern
The evidence pattern combined entity definition, comparison design, statistical enrichment, covariate-aware genetics, computational linking, and validation. Regulatory entities were defined from myeloid chromatin states using histone marks and open chromatin. AD SNP heritability enrichment was compared across regulatory annotations and against schizophrenia as a control trait using stratified LD score regression. Candidate target genes were inferred by integrating enhancer activity, open chromatin, eQTLs, enhancer-promoter linking, and transcriptomic data. Candidate functional variants were prioritized by fine-mapping, and one MS4A locus variant was functionally supported in hiPSC-derived microglia and human brain data. Boundary conditions include applicability mainly to myeloid regulatory programs represented in the input epigenomic datasets.

## Extends or contradicts
This study extends the authors' prior finding that AD risk alleles are enriched in myeloid-specific epigenomic annotations by showing that the enrichment is concentrated in active enhancers of monocytes, macrophages, and microglia and by nominating specific enhancer-linked genes and candidate functional variants. It does not contradict a specific prior paper listed in the provided wiki.

## Boundary conditions
Works when: The findings apply when the biological question concerns non-coding AD GWAS risk localization in human myeloid regulatory elements, especially active enhancers in monocytes, macrophages, and microglia. The approach is appropriate when GWAS summary statistics, LD information, myeloid chromatin annotations, open chromatin data, eQTLs, enhancer-promoter links, and transcriptomic data are available for integration.
Fails when: The approach is less informative for AD mechanisms mediated by non-myeloid brain cell types, rare or disease-stage-specific microglial states absent from the input datasets, brain-region-specific chromatin programs not represented in the data, ancestry-specific genetic architectures not captured by the GWAS or LD reference, and distal enhancer-gene relationships that cannot be resolved by available eQTL or enhancer-promoter linking data.
