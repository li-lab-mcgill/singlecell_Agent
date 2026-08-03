---
paper_id: functional_characterization_ad_2023
title: "Functional characterization of Alzheimer's disease genetic variants in microglia."
doi: "10.1038/s41588-023-01506-8"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC10939305/"
source_ids: {doc_id: "pmc:10939305", pmid: "37735198", pmcid: "10939305", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_peak_to_gene", "multiomic_integration", "atac_differential_accessibility"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["Learn what prior single-cell or chromatin studies show about AD-associated cis-regulatory elements, enhancer-target gene links, TF programs, and non-coding AD risk localization by brain cell type."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study integrated AD GWAS fine-mapping with microglia-specific chromatin accessibility and 3D epigenome annotations in human pluripotent stem cell-derived microglia. It prioritized 308 previously unreported AD risk variants across 181 microglial cCREs and used single-cell CRISPRi plus allele-specific expression analyses to connect regulatory variants to target genes and microglial phenotypes.

## Hypothesis framed
Noncoding AD GWAS variants contribute to disease risk by altering microglia-specific cis-regulatory elements, changing target gene expression, and producing AD-relevant microglial phenotypes.

## Questions answered
- Are AD GWAS variants enriched in microglial candidate cis-regulatory elements compared with other brain cell types?
- Does adding microglia-specific 3D chromatin architecture improve prioritization of functional AD regulatory variants beyond open chromatin annotation alone?
- Can single-cell CRISPRi identify target genes and phenotypic consequences for AD-associated microglial regulatory variants such as rs7922621?

## Key findings
The study prioritized 308 previously unreported AD risk variants at 181 microglial cCREs. Microglia-specific 3D epigenome annotation improved identification of likely functional regulatory variants compared with open chromatin annotation alone. IFNβ stimulation revealed immune-responsive AD risk loci, including loci affecting MS4A6A. Single-cell CRISPRi connected AD-associated cCREs to target genes, and allele-specific analyses showed that AD variants can produce allelic imbalance in target gene expression. rs7922621 was identified as the likely functional variant regulating TSPAN14 expression, and altered TSPAN14 expression reduced cell-surface ADAM10 and changed soluble TREM2 shedding.

## Methods used
AD GWAS fine-mapping; microglia-specific chromatin accessibility profiling; microglia-specific 3D chromatin interaction annotation; basal and IFNβ-stimulated hPSC-derived microglia experiments; transcriptomic and epigenomic profiling; cCRE prioritization; single-cell CRISPR interference screening; allele-specific expression analysis; functional follow-up at the TSPAN14 locus measuring cell-surface ADAM10 and soluble TREM2 shedding.

## Method and dataset
The study used human pluripotent stem cell-derived microglia generated from two hPSC lines, profiled under basal and IFNβ-stimulated conditions, with transcriptomic, chromatin accessibility, and 3D epigenomic data integrated with AD GWAS fine-mapping. The main variant set comprised 308 prioritized AD risk variants across 181 microglial cCREs. Single-cell CRISPRi perturbations were used to link regulatory elements to target gene expression. The approach assumes that hPSC-derived microglia capture relevant microglial regulatory programs, that microglia-specific open chromatin and 3D contacts nominate functional enhancer-target relationships, and that IFNβ stimulation models an AD-relevant immune-responsive regulatory state.

## Limitations
The experiments relied heavily on hPSC-derived microglia rather than primary adult human brain microglia in situ. Functional validation used a limited number of cell lines and genetic backgrounds. IFNβ stimulation models only a subset of the inflammatory conditions present in AD brain tissue. Although 308 variants were prioritized, only a subset received detailed mechanistic validation, with the deepest follow-up focused on the TSPAN14 locus. Additional validation is needed in primary human microglia, postmortem brain tissue, diverse ancestries, and in vivo models.

## Evidence pattern
Entity definition: microglial cCREs, AD GWAS variants, 3D chromatin-linked target genes, and allele-specific regulatory variants were explicitly defined. Comparison design: microglial cCRE enrichment was compared with other brain cell types, and prioritization using 3D chromatin architecture was compared with open chromatin annotation alone. Statistical unit: AD GWAS variants, cCREs, hPSC-derived microglia, CRISPRi perturbations, and target gene expression responses. Metrics: heritability enrichment, variant prioritization counts, enhancer-target gene links, allele-specific expression imbalance, and phenotypic measures including cell-surface ADAM10 and soluble TREM2 shedding. Validation: single-cell CRISPRi screening, allele-specific expression analyses, and functional assays at the rs7922621-TSPAN14 axis. Boundary conditions: evidence is strongest for hPSC-derived microglia under basal and IFNβ-stimulated conditions and for loci with microglia-specific chromatin accessibility and 3D contacts.

## Extends or contradicts
This extends prior observations that AD heritability is enriched in microglial cis-regulatory elements by moving from enrichment and annotation to experimentally validated enhancer-variant-target gene links and microglial phenotypes. It does not contradict the summarized prior findings.

## Boundary conditions
Works when: The approach is applicable when AD or other disease GWAS fine-mapping data can be integrated with cell-type-specific chromatin accessibility and 3D chromatin interaction maps, especially in microglia or microglia-like cells. It is best supported for regulatory variants located in microglial cCREs that are active under basal or IFNβ-stimulated conditions and for target genes measurable by single-cell CRISPRi expression readouts.
Fails when: The findings may not generalize to regulatory states absent from hPSC-derived microglia, to adult in vivo microglia-specific programs not captured by the differentiation system, to AD inflammatory contexts not modeled by IFNβ, or to loci lacking detectable microglial chromatin accessibility or 3D contacts. Mechanistic claims are weaker for the many prioritized variants that were not individually validated.
