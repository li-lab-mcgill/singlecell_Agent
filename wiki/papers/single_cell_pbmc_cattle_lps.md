---
paper_id: single_cell_pbmc_cattle_lps
title: "Single-cell transcriptomic and chromatin accessibility analyses of dairy cattle peripheral blood mononuclear cells and their responses to lipopolysaccharide."
doi: "10.1186/s12864-022-08562-0"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9063233/"
source_ids: {doc_id: "pmc:9063233", pmid: "35501711", pmcid: "9063233", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "atac_motif_analysis", "rna_differential_expression"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["Retrieve GLUE paper and summarize PBMC biological validation patterns for RNA+ATAC integration."]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
Generated the first reported single-cell RNA-seq and single-cell ATAC-seq profiles of bovine PBMCs (26,141 cells from 4 Holstein cows) stimulated in vitro with LPS (2 μg/ml, 0/2/4/8 h). Identified seven major immune cell types, characterized LPS-driven transcriptional and chromatin-accessibility changes (notably in monocytes and dendritic cells), and linked subsets of LPS-responsive genes to Holstein GWAS traits.

## Hypothesis framed
Single-cell transcriptomic and chromatin accessibility profiling of bovine PBMCs can identify cell-type–specific transcriptional and regulatory responses to LPS stimulation that are concordant across RNA and ATAC modalities and relevant to complex traits in Holstein cattle.

## Questions answered
- Which major PBMC cell types are present in lactating Holstein cattle and how many single-cell profiles were recovered?
- Does LPS stimulation induce coordinated, cell-type-specific changes in gene expression and chromatin accessibility (and which TF programs are implicated)?
- Are LPS-responsive genes enriched for associations with complex traits in Holstein cattle (from large-scale GWAS)?

## Key findings
Analyzed 26,141 single-cell transcriptomes (7,107 control; 9,174 2 h; 6,741 4 h; 3,119 8 h) and matched scATAC data from PBMCs pooled from four 2-year-old lactating Holsteins. Identified seven major cell types: CD4 T cells, CD8 T cells, B cells, monocytes, natural killer cells, innate lymphoid cells, and dendritic cells. LPS (2 μg/ml) increased cell-cycle and differentiation programs and global chromatin accessibility. Monocytes and dendritic cells showed strongest activation: upregulated TLR4, activation of NF-κB family members (NFKB1, NFKB2, RELB), IRF programs, and increased transcription of pro-inflammatory cytokines/chemokines (e.g., CCL2, CXCL2). scATAC-seq showed increased accessibility at regulatory sites and enrichment of corresponding TF motifs. Integration with GWAS of 45 Holstein traits found subsets of LPS-induced DEGs significantly associated with immune-related health, milk production, and body conformation traits.

## Methods used
10x Genomics single-cell RNA-seq and single-cell ATAC-seq; Seurat-based clustering and marker-driven cell-type assignment; time-course differential expression analyses across 0, 2, 4, 8 h; scATAC-based chromatin accessibility analysis and TF motif enrichment; regulatory interaction analyses linking peaks to genes; integration of DEGs with large-scale Holstein GWAS (45 traits); gene ontology enrichment analyses.

## Method and dataset
Paired scRNA-seq and scATAC-seq (10x Genomics chemistry) on bovine PBMCs pooled from four 2-year-old lactating Holstein cows, LPS-treated in vitro at 2 μg/ml sampled at 0, 2, 4, 8 hours; ~26,141 RNA cells post-QC. Assumes that pooled in vitro PBMC stimulation reflects cell-type–specific LPS responses and that marker-based labels transfer between RNA and ATAC modalities.

## Limitations
Small sample size (four animals pooled) limiting assessment of inter-individual variation; in vitro LPS stimulation may not recapitulate in vivo infection dynamics; limited time-course resolution (no <2 h or >8 h sampling); no orthogonal functional validations (e.g., ChIP-seq or perturbation); potential underrepresentation of rare/low-abundance cell types; no detailed cross-method benchmarking metrics for RNA+ATAC integration.

## Evidence pattern
entity_definition (marker-based cell-type calls validated across RNA and ATAC), comparison_design (time-course 0/2/4/8 h LPS vs control), statistical_unit (pooled cells from 4 cows; per-cell analyses; counts: 7,107 control; 9,174 2h; 6,741 4h; 3,119 8h), effect_metric (differential expression, chromatin accessibility changes, TF motif enrichment), controls_covariates (untreated 0 h controls; pooling of 4 animals noted), validation (cross-modal concordance: scRNA marker expression supported by scATAC accessibility and TF motif activity), boundary_conditions (results reported for 2 μg/ml LPS, 0–8 h in vitro), analyses_used (Seurat clustering, DEG testing, TF motif enrichment, peak-to-gene/regulatory interaction analyses, GWAS intersection).

## Extends or contradicts
Extends prior bulk-tissue bovine LPS response studies by providing single-cell resolution and multi-omic (RNA+ATAC) evidence; findings are consistent with prior knowledge that NF-κB and IRFs mediate LPS-induced innate immune activation in myeloid cells.

## Boundary conditions
Works when: Data are paired or matched scRNA-seq and scATAC-seq from bovine PBMCs (10x Genomics chemistry), total cells on the order of tens of thousands (≈26k), samples pooled from adult Holstein cattle, in vitro LPS stimulation at ~2 μg/ml, and sampling in the 0–8 h post-stimulation window; major/abundant immune cell types (monocytes, DCs, T/B/NK cells) are present in sufficient numbers for per-cell-type analyses.
Fails when: Applied to in vivo infection time courses beyond 8 h or earlier than 2 h where dynamics differ; different species (e.g., human) without validation; very small datasets (<<1,000 cells) or single-animal samples where pooling effects or inter-individual variation dominate; different LPS doses or stimulation conditions; when rare cell types are the focus and are under-represented; when orthogonal validation of regulatory links is required (no ChIP/perturbation done).
