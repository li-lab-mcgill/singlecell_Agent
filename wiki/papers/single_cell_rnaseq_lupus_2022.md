---
paper_id: single_cell_rnaseq_lupus_2022
title: "Single-cell RNA-seq reveals cell type-specific molecular and genetic associations to lupus."
doi: "10.1126/science.abf1970"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9297655/"
source_ids: {doc_id: "pmc:9297655", pmid: "35389781", pmcid: "9297655", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_cell_type_annotation", "rna_differential_abundance", "rna_differential_expression"]
retrieval_goals: ["prior_findings"]
retrieval_intents: ["Canonical PBMC cell type and subtype marker genes expected in human PBMC scRNA-seq and corresponding ATAC motif/peak signatures."]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
This study used multiplexed single-cell RNA-seq (mux-seq) on >1.2 million PBMCs from 162 adult SLE cases and 99 controls to define cell type- and state-specific transcriptional alterations in SLE and to map cell type–specific cis-eQTLs linking genetic variation to expression. The work identifies monocyte-dominant type I interferon signatures, reduced naïve CD4+ T cells (especially in Asian-ancestry patients), expanded GZMH+ cytotoxic CD8+ T cells, and uses genotype integration to prioritize disease loci.

## Hypothesis framed
Circulating immune cell composition and cell type–specific gene expression (including IFN-stimulated programs) differ between adult SLE cases and controls and these differences can be linked to genetic variation through cell type–specific cis-eQTL mapping.

## Questions answered
- Which PBMC cell types and cell states show altered abundance or gene expression in adult SLE compared to healthy controls?
- Do cell type–specific cis-eQTLs in PBMCs colocalize with or help prioritize SLE GWAS loci?
- Can cell type–specific expression signatures classify SLE cases versus controls and define molecular patient subtypes?

## Key findings
Analyzed >1.2 million PBMCs from 162 SLE cases and 99 controls across Asian and European ancestries; identified a reduction in naïve CD4+ T cells (statistically enriched in patients of Asian ancestry) and expansion of repertoire-restricted GZMH+ cytotoxic CD8+ T cells in cases; classical and nonclassical monocytes showed the strongest type I IFN-stimulated gene (ISG) signatures, with monocyte ISG expression inversely correlated with naïve CD4+ T cell abundance; cell type–specific expression signatures reliably discriminated cases from controls and defined two molecular subtypes of patients; mapped shared and cell type–specific cis-eQTLs across eight annotated PBMC cell populations and showed that cell type–specific eQTLs are enriched in corresponding open chromatin regions; joint eQTL–GWAS and genotype×IFN interaction analyses prioritized SLE-associated loci and identified variants whose expression effects are modified by interferon activation.

## Methods used
Multiplexed single-cell RNA sequencing (mux-seq) of PBMCs; cell type annotation and clustering across eight immune populations; differential abundance and differential expression testing between cases and controls; correlation analyses (e.g., monocyte ISG vs naïve CD4+ abundance); predictive modeling/classification to discriminate cases vs controls and define molecular subtypes; dense genotype collection and a matrix-decomposition approach to map shared and cell type–specific cis-eQTLs; enrichment analyses of eQTLs in cell-specific open chromatin; joint eQTL–GWAS colocalization/fine-mapping and genotype-by-IFN interaction tests.

## Method and dataset
Mux-seq scRNA-seq on peripheral blood mononuclear cells (PBMCs), totaling >1.2 million cells sampled from 261 adult donors (162 SLE cases, 99 healthy controls) of Asian and European ancestry; integrated with dense genotype data per donor and cell-type open chromatin annotations for enrichment analyses. Assumptions include adequate per-donor and per-cell-type cell counts to estimate cell type proportions and map cis-eQTLs, and that cross-sectional sampling captures disease-associated steady-state differences.

## Limitations
Restricted to circulating PBMCs from adults (no tissue-resident or pediatric populations); cross-sectional design limits causal and temporal inference; potential confounding by medications and clinical heterogeneity despite adjustments; limited power for detection of trans-eQTLs and very rare cell-state associations; lack of functional validation for prioritized variants; did not provide a comprehensive per-cell-type ATAC peak/motif signature list.

## Evidence pattern
entity_definition, statistical_unit, comparison_design, effect_metric, controls_covariates, boundary_conditions, analysis_used

## Extends or contradicts
Extends prior bulk and smaller-scale single-cell studies reporting type I interferon signatures and immune dysregulation in SLE by providing large-cohort, cell type–resolved transcriptional maps and linking genetic variation to cell type–specific expression.

## Boundary conditions
Works when: Applies to adult peripheral blood samples processed with multiplexed scRNA-seq (mux-seq) and dense genotyping, with cohort sizes on the order of hundreds of donors (here 261 donors) and total cell counts on the order of >1M; works when per-donor and per-cell-type cell counts are sufficient (tens-to-hundreds of cells per donor per cell type) to estimate proportions and map cis-eQTLs and when patient ancestry is represented (Asian and European in this study).
Fails when: Does not apply to pediatric SLE or tissue-resident immune populations; unreliable when donor count is small (e.g., <100 donors) or when per-donor per-cell-type cell counts are very low (e.g., <50 cells), which undermines eQTL detection and differential abundance estimates; fails to capture temporal dynamics (longitudinal changes) due to cross-sectional design; findings may not generalize when genotype data or cell-type-specific open chromatin annotations are absent.
