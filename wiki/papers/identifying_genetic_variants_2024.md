---
paper_id: identifying_genetic_variants_2024
title: "Identifying genetic variants that influence the abundance of cell states in single-cell data."
doi: "10.1038/s41588-024-01909-1"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12140807/"
source_ids: {doc_id: "pmc:12140807", pmid: "39327486", pmcid: "12140807", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_differential_abundance"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Determine how single-cell disease-control studies statistically test cell-type/state abundance and avoid confounding molecular differential state claims with compositional shifts and donor/batch covariates."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This paper introduces Genotype-Neighborhood Associations (GeNA), a method for testing whether genetic variants are associated with the abundance of fine-grained cell states in single-cell RNA-seq data without requiring predefined cell-state labels. Applied to peripheral blood single-cell RNA-seq from 969 genotyped individuals, GeNA found genotype-associated shifts in immune cell-state abundance, including an NK-cell state linked to tumor necrosis factor response programs and psoriasis risk.

## Hypothesis framed
Genetic variants associated with disease risk alter the relative abundance of granular single-cell transcriptional states, and these effects can be detected by testing variant associations with donor-level neighborhood abundance patterns rather than with predefined cell-type labels.

## Questions answered
- Can genome-wide genotype associations with granular cell-state abundance be tested in single-cell RNA-seq without predefining cell states?
- Which genetic loci are associated with relative abundance shifts of immune cell states in peripheral blood single-cell RNA-seq from 969 individuals?
- Can a cell-state abundance QTL identify disease-relevant immune states, such as NK cells expressing tumor necrosis factor response programs linked to psoriasis risk?

## Key findings
In peripheral blood single-cell RNA-seq from 969 genotyped individuals, GeNA identified five independent loci associated with shifts in the relative abundance of immune cell states. The rs3003-T allele was associated with increased abundance of natural killer cells expressing tumor necrosis factor response programs with P = 1.96 × 10^-11, and this cell-state abundance QTL colocalized with increased genetic risk for psoriasis.

## Methods used
GeNA constructs a nearest-neighbor graph from single-cell RNA-seq data, defines local cell-state neighborhoods, computes each individual's fractional abundance in each neighborhood to form a Neighborhood Abundance Matrix, applies principal component analysis to summarize donor-level neighborhood abundance variation, and tests each genetic variant for association with linear combinations of the top neighborhood-abundance principal components while adjusting for demographic and technical sample-level covariates.

## Method and dataset
Method: Genotype-Neighborhood Associations for cell-state abundance QTL discovery. Data: peripheral blood single-cell RNA-seq from 969 genotyped individuals. Experimental design: genome-wide association scan of donor-level genotype dosage against donor-level relative abundance patterns across nearest-neighbor-defined cell-state neighborhoods. Assumptions: the nearest-neighbor graph captures biologically meaningful cell states, per-individual fractional neighborhood abundance is a valid donor-level compositional phenotype, major abundance variation can be summarized by top PCA components, and relevant demographic and technical confounders are included as covariates.

## Limitations
The main application was limited to peripheral blood single-cell RNA-seq, and available data did not permit application to primary solid tissue single-cell datasets. Power depends on cohort size, genotype availability, number of cells sampled per donor, batch correction quality, and neighborhood construction quality. GeNA detects genotype associations with cell-state abundance but does not prove causal mechanisms or distinguish whether variants affect cell-state identity, cell survival, differentiation, trafficking, or upstream biological processes.

## Evidence pattern
Entity definition: cell-state abundance QTLs are defined as genetic variants associated with donor-level abundance of local neighborhoods in a single-cell nearest-neighbor graph. Statistical unit: individual donor, not cell. Metric: fractional abundance of each donor's cells in neighborhoods, reduced by PCA. Covariates: demographic and technical sample-level covariates can be included in variant association tests. Analysis used: genome-wide genotype association testing with one association test per variant over top neighborhood-abundance principal components. Boundary conditions: demonstrated on peripheral blood single-cell RNA-seq from 969 genotyped individuals.

## Extends or contradicts


## Boundary conditions
Works when: Works when single-cell RNA-seq data are available from many genotyped individuals, cells can be embedded into a meaningful nearest-neighbor graph, each donor has enough sampled cells to estimate fractional neighborhood abundance, and relevant donor-level demographic and technical covariates are available for adjustment.
Fails when: Not applicable when genotype data are unavailable, donor/sample size is too small for genetic association testing, cell sampling per donor is too sparse to estimate neighborhood abundance, neighborhood construction is dominated by batch effects, or unmodeled disease, treatment, ancestry, or technical covariates confound genotype-abundance associations. It does not by itself establish causal mechanisms or separate direct cell-state effects from effects on survival, differentiation, or trafficking.
