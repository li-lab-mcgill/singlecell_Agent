---
paper_id: epstein_barr_evasion_2023
title: "Epstein-Barr virus evades restrictive host chromatin closure by subverting B cell activation and germinal center regulatory loci."
doi: "10.1016/j.celrep.2023.112958"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC10559315/"
source_ids: {doc_id: "pmc:10559315", pmid: "37561629", pmcid: "10559315", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_motif_analysis", "atac_peak_to_gene", "multiomic_integration"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["Summarize lineage-defining TF motif and accessibility patterns in human PBMC scATAC-seq"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
This study profiles chromatin accessibility dynamics in primary human peripheral B cells infected in vitro with EBV using scATAC-seq (97,191 cells across days 0,2,5,8) integrated with scRNA-seq and ChIP-seq to show that EBV drives bifurcating chromatin trajectories: an accessibility-reduced arrested state and a proliferative GC-like state. The work identifies EBV nuclear antigens and host TFs (validated: MEF2C, NFE2L2) as regulators of these phenotypes and demonstrates EBNA-associated regulation of immune-evasion loci including CD274/PD-L1.

## Hypothesis framed
Epstein-Barr virus (EBV) remodels host chromatin accessibility in individual human B cells during early de novo infection, and specific viral (EBNAs) and host transcriptional regulators (e.g., MEF2C, NFE2L2) drive distinct infection phenotypes including proliferative GC-like programs and immune-evasion gene expression.

## Questions answered
- Does EBV infection produce distinct single-cell chromatin accessibility trajectories in primary human B cells during early infection?
- Do proliferative EBV+ B cells acquire germinal-center-like TF motif and accessibility profiles despite downregulation of canonical GC TF BCL6?
- Are predicted host regulators (MEF2C, NFE2L2) and EBNA-associated regulatory loci functionally required for EBV-induced GC-like phenotypes and PD-L1 (CD274) regulation?

## Key findings
Analyzed 97,191 high-quality scATAC-seq B cells (days 0,2,5,8). Found a subset of EBV+ cells with genome-wide per-cell accessibility reductions of ~20–40%. Single-cell trajectories bifurcate by day 2 into EBV+ low-ATAC (arrest/sensing/DNA-damage-linked) and EBV+ high-ATAC (proliferative) branches. Proliferative EBV+ cells acquire DZ, LZ, and post-GC chromatin accessibility and TF-motif landscapes despite BCL6 downregulation. Integration implicates EBV nuclear antigens in phenotype-specific regulation of activation, survival, and immune-evasion programs, including EBNA-associated control of CD274/PD-L1. Cas9-RNP knockouts validated host TF regulators MEF2C and NFE2L2 and EBNA-associated regulatory control at loci (e.g., affecting CD274 expression). Population-level (ensemble) peak counts increased after infection while per-cell accessible peak counts decreased along trajectories.

## Methods used
Single-cell ATAC-seq (time course days 0,2,5,8), single-cell RNA-seq integration, ChIP-seq for EBNA and TF binding, pseudotime and trajectory inference, motif enrichment analysis, cis-regulatory peak-to-gene prediction (correlation-based), differential accessibility, and functional validation via Cas9-RNP gene knockouts in lymphoblastoid cell lines.

## Method and dataset
Applied scATAC-seq to primary human peripheral B cells from two donors infected in vitro with B95-8 EBV, profiling 97,191 cells after QC across four timepoints (days 0,2,5,8). Analysis retained the top 50% differentially accessible peaks for downstream analyses. Integrated scRNA-seq and ChIP-seq data for peak-to-gene linking and regulator attribution. Assumes that correlations between peak accessibility and expression across single cells reflect cis-regulatory links and that motif accessibility enrichment reflects TF activity despite scATAC sparsity.

## Limitations
In vitro infection of primary B cells from only two donors (no donor age/sex metadata) limits generalizability and in vivo relevance. scATAC-seq sparsity likely underestimates accessible loci and may bias motif and peak-to-gene inference. Infection is asynchronous and heterogeneous, complicating temporal resolution. Functional validation covered a limited subset of predicted regulators/loci (MEF2C, NFE2L2, select EBNA-associated loci). No PBMC-wide multi-lineage comparisons or external PBMC atlases were used.

## Evidence pattern
Entity definition: primary human peripheral B cells infected with B95-8 EBV; Statistical unit: single cells (n=97,191 after QC); Comparison design: time-course (days 0,2,5,8) and trajectory-based bifurcation into EBV+ low-ATAC vs high-ATAC branches; Effect metrics: per-cell accessible peak counts, % per-cell accessibility change (~20–40% reductions in subset), motif enrichment scores, peak-to-gene correlation; Covariates: donor (two donors), infection status/timepoint; Validation: Cas9-RNP knockouts (MEF2C, NFE2L2) and ChIP-seq showing EBNA binding at predicted loci; Analysis used: pseudotime/trajectory inference, motif enrichment, cis peak-to-gene prediction.

## Extends or contradicts
Extends prior bulk studies that linked EBV to chromatin and transcriptional changes by resolving single-cell heterogeneity and identifying cell-state-specific chromatin remodeling and regulators; does not directly contradict major prior findings but shows GC-like chromatin programs can arise despite BCL6 downregulation.

## Boundary conditions
Works when: Applies to primary human peripheral B cells infected in vitro with B95-8 EBV sampled across early infection (days 0–8), with high cell counts (tens of thousands; demonstrated on ~97k cells), availability of matched scRNA-seq and ChIP-seq for integration, and peak filtering (top ~50% differential peaks) to mitigate noise.
Fails when: Not applicable or expected to fail for low cell-count scATAC datasets (<10,000 cells), other cell types or whole PBMC multi-lineage datasets without B cell enrichment, in vivo infection contexts or different EBV strains without validation, datasets lacking matched scRNA or ChIP data for peak-to-gene linkage, or when scATAC sparsity is severe and prevents reliable per-cell peak and motif inference.
