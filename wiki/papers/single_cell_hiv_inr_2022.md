---
paper_id: single_cell_hiv_inr_2022
title: "Single-cell sequencing resolves the landscape of immune cells and regulatory mechanisms in HIV-infected immune non-responders."
doi: "10.1038/s41419-022-05225-6"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9532384/"
source_ids: {doc_id: "pmc:9532384", pmid: "36195585", pmcid: "9532384", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_cell_type_annotation", "atac_differential_accessibility", "atac_motif_analysis"]
retrieval_goals: ["prior_findings"]
retrieval_intents: ["Canonical PBMC cell type and subtype marker genes expected in human PBMC scRNA-seq and corresponding ATAC motif/peak signatures."]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
This paper applies 10x single-cell RNA-seq and single-cell ATAC-seq plus flow cytometry to PBMCs from HIV-1-infected immune non-responders (INRs) and responders (IRs) to map immune-cell composition and regulatory states. It identifies a depletion of MAIT cells in INRs and implicates MAIT-specific mitochondrial dysfunction (reduced TFAM and PPARA, diminished mitochondrial fitness) as a mechanism underlying impaired antibacterial immunity in INRs.

## Hypothesis framed
Mitochondrial dysfunction in MAIT cells contributes to impaired immune reconstitution and antibacterial immunity in HIV-1-infected immune non-responders.

## Questions answered
- Are MAIT cells reduced in frequency in PBMCs from HIV-infected immune non-responders compared with immune responders?
- Do MAIT cells from INRs show transcriptional, chromatin-accessibility, and functional evidence of mitochondrial dysfunction (including reduced TFAM and PPARA expression)?

## Key findings
Droplet-based scRNA-seq (10x) on PBMCs from 2 INRs and 2 IRs produced 12,086 cells after QC and identified 11 major immune subsets. MAIT-cell frequency was reduced in INRs relative to IRs. MAIT cells from INRs showed transcriptional signatures of impaired mitochondrial function and increased apoptosis signaling. scATAC-seq and flow cytometry confirmed diminished mitochondrial fitness in MAIT cells from INRs. MAIT cells in INRs had lower expression of mitochondrial regulators TFAM and PPARA.

## Methods used
10x Genomics droplet-based single-cell RNA-seq, single-cell ATAC-seq, UMAP-based clustering, canonical marker annotation for cell-type assignment, differential gene-expression analysis, chromatin-accessibility and motif analysis, and flow-cytometry assays of mitochondrial function.

## Method and dataset
Paired single-cell transcriptome and chromatin-accessibility profiling (10x scRNA-seq and scATAC-seq) on PBMCs from 2 immune non-responders and 2 immune responders (total 12,086 scRNA-seq cells after QC). UMAP clustering and marker-based annotation identified 11 immune subsets; downstream differential analyses focused on MAIT cells. Assumes canonical marker genes correctly annotate PBMC subsets and that cell numbers per subject are sufficient to detect MAIT-cell differences despite very small cohort size.

## Limitations
Very small cohort (n=2 INRs, n=2 IRs) limiting statistical power and generalizability; cross-sectional PBMC sampling cannot establish causality or tissue-specific effects; potential confounders (age, baseline CD4, co-infections, treatment duration) not fully controlled; limited functional validation beyond flow mitochondrial assays.

## Evidence pattern
entity_definition, validation, comparison_design, statistical_unit, boundary_conditions

## Extends or contradicts
Extends prior observations of altered peripheral immune composition in chronic infection by specifically implicating MAIT-cell mitochondrial dysfunction (reduced TFAM and PPARA, lower mitochondrial fitness) in HIV-infected INRs.

## Boundary conditions
Works when: Applies to 10x Genomics PBMC scRNA-seq and scATAC-seq data from HIV-1-infected subjects on suppressive HAART where MAIT cells are present at detectable frequencies; total cell counts on the order of ~10k cells and comparable sequencing depth; orthogonal flow-cytometry mitochondrial assays are available for validation.
Fails when: Findings do not generalize when cohorts are larger and heterogeneous without controlling confounders, when MAIT cells are absent or extremely rare in the dataset, when sampling is from tissue-resident (non-PBMC) compartments, or when no orthogonal measures (e.g., flow cytometry) confirm mitochondrial phenotypes; statistical conclusions are unreliable for n<<10 subjects per group.
