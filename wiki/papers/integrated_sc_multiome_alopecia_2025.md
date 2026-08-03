---
paper_id: integrated_sc_multiome_alopecia_2025
title: "Integrated single-cell chromatin and transcriptomic analyses of peripheral immune cells in patients with alopecia areata."
doi: "10.3389/fimmu.2025.1565241"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12263667/"
source_ids: {doc_id: "pmc:12263667", pmid: "40672948", pmcid: "12263667", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "atac_motif_analysis", "atac_peak_to_gene"]
retrieval_goals: ["prior_findings"]
retrieval_intents: ["Canonical PBMC cell type and subtype marker genes expected in human PBMC scRNA-seq and corresponding ATAC motif/peak signatures."]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
This study generated an integrated single-cell transcriptomic and chromatin accessibility atlas of peripheral blood immune cells from alopecia areata (AA) patients and controls, profiling 32,453 high-quality cells across ~36 immune subtypes and identifying 42,248 significant ATAC peaks. The integrative analysis links cell-type-resolved transcriptional markers (e.g., GZMB, GNLY, MHC genes) with matched chromatin accessibility and TF motif signatures, highlighting peripheral immune remodeling correlated with disease severity and nominating monocytes, NK cells and memory T cells as signaling hubs and potential therapeutic targets.

## Hypothesis framed
Peripheral blood immune cells in patients with alopecia areata exhibit coordinated transcriptional and chromatin-accessibility alterations that scale with disease severity and identify cellular hubs and pathways amenable to therapeutic modulation.

## Questions answered
- Do peripheral blood immune cells in alopecia areata exhibit transcriptional and chromatin accessibility changes that correlate with disease severity?
- Which PBMC cell types show the greatest epigenetic remodeling in AA (which cell types have most differential ATAC peaks)?
- Are canonical proinflammatory and antigen-presentation signatures (TH1/TH2/TH17, IFN-stimulated genes, cytotoxic granule genes, MHC I/II) upregulated in peripheral immune cells in severe AA?

## Key findings
Analyzed 32,453 high-quality PBMCs across ~36 annotated immune subtypes (from a cohort of 35 individuals, with a profiled subset of 16 samples: 5 severe AA, 6 mild AA, 5 controls). Identified 42,248 significant ATAC peaks; largest chromatin accessibility remodeling occurred in CD14+ monocytes, NK cells, and CD8+ T cells. Severe AA showed increased transcriptional heterogeneity, activation of cytokine/chemokine and antigen-presentation pathways, and enrichment of TH1/TH2/TH17 signatures. Effector populations (proinflammatory monocytes, CD8+ effector memory T cells, NK subsets) exhibited coordinated upregulation of IFN-stimulated genes, cytotoxic granule genes including GZMB and GNLY, and MHC class I and II genes. Mild AA displayed elevated exhaustion markers in double-negative T cells and increased apoptosis signatures in myeloid populations. Pseudotime and TF-motif analyses indicated altered differentiation trajectories; inferred intercellular communication nominated monocytes, NK cells, and memory T cells as peripheral signaling hubs.

## Methods used
Paired/integrated single-cell RNA-seq and single-cell ATAC-seq on PBMCs; single-cell QC and filtering; dimensionality reduction and clustering; marker-based cell-type annotation; differential gene expression analysis; differential chromatin accessibility analysis (peak calling and significance testing yielding 42,248 peaks); transcription factor motif enrichment on ATAC peaks; pseudotime/trajectory inference; inferred cell–cell communication network analysis; pathway enrichment analyses.

## Method and dataset
Integrated single-cell multiomic profiling (scRNA-seq + scATAC-seq) of peripheral blood mononuclear cells collected from 35 individuals (12 severe AA, 11 mild AA, 12 healthy controls); a high-quality subset of 16 samples (5 severe, 6 mild, 5 controls) was profiled and after QC 32,453 cells across ~36 immune subtypes were analyzed. Analyses assume adequate sequencing depth for ATAC to detect tens of thousands of peaks, paired modal measurements or reliable cross-modality integration per cell, standard single-cell QC thresholds, and marker-based annotation for subtype assignment.

## Limitations
Relatively small profiled subset (16 samples) limiting statistical power and generalizability; cross-sectional design with no longitudinal sampling or functional perturbation validation; inclusion of some participants with stable Hashimoto's thyroiditis that may confound immune signals; peripheral blood may not capture lesional tissue microenvironment; variability in sequencing/library metrics across samples could affect sensitivity for rare states; per-subtype genomic peak coordinates and per-peak statistical tables are not provided in the summary.

## Evidence pattern
entity_definition; comparison_design (controls vs mild vs severe AA); statistical_unit = cells nested within donors; effect_metric = differential expression and differential accessibility (counts/peak significance), pathway enrichment, motif enrichment; covariates noted (disease severity, some participants with Hashimoto's); validation = integrated RNA+ATAC concordance and consistency with lesional signatures; analyses used = clustering, DE, DA, motif enrichment, pseudotime, cell–cell communication inference.

## Extends or contradicts
Extends prior AA studies that focused on lesional scalp tissue by demonstrating systemic peripheral immune transcriptional and epigenetic alterations correlated with disease severity; does not report direct contradictions with prior published lesional findings and in fact notes parallels (e.g., cytotoxic and IFN signatures).

## Boundary conditions
Works when: Applies when studying human PBMCs with paired or well-integrated scRNA and scATAC data, sequencing depth sufficient to call tens of thousands of ATAC peaks (as in this study: ~42k peaks), and cohort design includes multiple donors per condition (≥5 donors per group as in profiled subset). Works when major PBMC populations (monocytes, NK cells, CD8+ T cells, memory T cells) are present at detectable frequencies and standard single-cell QC/cluster annotation pipelines are applicable.
Fails when: Findings/methods are unreliable when sample sizes per group are very small (<5 donors), when modalities are unpaired and cannot be robustly integrated, when ATAC sequencing depth is insufficient to detect large numbers of peaks, when comorbid autoimmune diseases are prevalent and uncontrolled (confounding signals), when investigating tissue-resident lesional microenvironments rather than peripheral blood, or when longitudinal/dynamic inference is required (cross-sectional design prevents causal/dynamic claims).
