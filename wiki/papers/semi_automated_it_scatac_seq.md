---
paper_id: semi_automated_it_scatac_seq
title: "Semi-automated IT-scATAC-seq profiles cell-specific chromatin accessibility in differentiation and peripheral blood populations."
doi: "10.1038/s41467-025-57931-2"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC11914533/"
source_ids: {doc_id: "pmc:11914533", pmid: "40097444", pmcid: "11914533", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_motif_analysis", "atac_peak_to_gene", "atac_cell_type_annotation"]
retrieval_goals: ["prior_findings"]
retrieval_intents: ["Canonical PBMC cell type and subtype marker genes expected in human PBMC scRNA-seq and corresponding ATAC motif/peak signatures."]
extends: ["systematic_benchmarking_scatac_2024", "benchmarking_cell_type_annotation_2022"]
added: 2026-05-15
session: unknown
---

## Summary
Introduces IT-scATAC-seq, a semi-automated indexed-Tn5 single-cell ATAC-seq workflow using a three-round barcoding strategy and 384-well plate processing to generate high-quality chromatin accessibility profiles at ~10,000 cells/day and an estimated reagent cost of ≈$0.01 per cell. Benchmarks show library complexity, TSS enrichment, and mitochondrial read fractions comparable to or better than plate-based and 10x methods, and the method resolves cell-type-specific regulatory programs in human PBMCs and dynamic chromatin states during early mouse ESC differentiation.

## Hypothesis framed
A semi-automated indexed-Tn5 scATAC-seq workflow (IT-scATAC-seq) using three-round barcoding and 384-well plate processing can produce single-cell chromatin accessibility data at scale (~10,000 cells/day) with per-cell reagent cost ≈$0.01 while maintaining library complexity, TSS enrichment, and low mitochondrial contamination comparable to or better than existing plate-based and microfluidic methods.

## Questions answered
- Does IT-scATAC-seq achieve comparable library complexity, TSS enrichment, and mitochondrial read fraction to plate-based and 10x Genomics scATAC-seq while substantially reducing per-cell reagent cost?
- Can IT-scATAC-seq resolve cell-type-specific regulatory programs in human PBMCs and capture dynamic chromatin remodeling during early mouse ESC differentiation?

## Key findings
IT-scATAC-seq produced single-cell accessibility data with robust library complexity, strong TSS enrichment, and low mitochondrial contamination comparable to or exceeding plate-based and 10x methods; the workflow scaled to approximately 10,000 cells processed in a single day and reduced estimated reagent cost to ≈$0.01 per cell. Biologically, IT-scATAC-seq resolved cell-type-specific regulatory programs in human PBMCs (cluster-level annotations, motif enrichment and peak signatures, gene-activity associations) and identified an intermediate chromatin-accessible state with both pluripotent and lineage-specific regulatory element accessibility during early mouse ESC differentiation. Method validation included species-mixing for doublet assessment and benchmarking against multiple published scATAC datasets.

## Methods used
Assembly of indexed Tn5 transposomes; parallel bulk transposition reactions; fluorescence-activated nuclei sorting (FANS) into 384-well plates; three-round barcoding (well-specific lysis/PCR), pooling, and final PCR to add Illumina adapters; optional liquid-handler automation for plate processing; QC and downstream analysis using ArchR; motif enrichment and gene-activity association analyses; benchmarking vs plate-based, C1, 10x Genomics, sci-ATAC, CH-ATAC-seq, HydropATAC datasets; species-mixing experiments for doublet validation.

## Method and dataset
IT-scATAC-seq (experimental protocol) applied to single-cell ATAC-seq data from mouse embryonic stem cells undergoing early differentiation and human peripheral blood mononuclear cells (PBMCs); produced datasets up to ~10,000 cells per run (single-day processing); experimental design included bulk indexed tagmentation followed by FANS into 384-well plates, three-round barcoding, and benchmarking against publicly available scATAC datasets; assumes availability of FANS, a liquid-handling platform, and in-house capacity to assemble indexed Tn5 transposomes.

## Limitations
Requires access to fluorescence-activated nuclei sorting (FANS) and a liquid-handling platform and also requires in-house assembly of indexed Tn5 transposomes, limiting immediate adoption. Reported per-cell reagent cost likely excludes capital equipment and labor. Multiplexed bulk tagmentation and sorting introduce barcode collision/doublet risk. Benchmarking and biological validation were limited to the datasets and cell types tested (mouse ESC differentiation and human PBMCs) and do not provide exhaustive marker lists or peak/motif mappings for all PBMC sub-subtypes and rare cell types.

## Evidence pattern
entity_definition; comparison_design; statistical_unit; effect_metric; validation; boundary_conditions. Supported by benchmarking comparisons using ArchR vs multiple published scATAC datasets, QC metrics (fragments per cell, TSS enrichment, mitochondrial read fraction, library complexity), and species-mixing experiments for doublet validation.

## Extends or contradicts
Extends prior systematic benchmarking of scATAC protocols and cell-type annotation benchmarks (systematic_benchmarking_scatac_2024, benchmarking_cell_type_annotation_2022) by introducing a low-cost, semi-automated indexed-Tn5 protocol and demonstrating comparable or improved QC metrics versus existing methods.

## Boundary conditions
Works when: Works when labs have access to FANS (nuclei sorter), a 384-well-compatible liquid-handling platform (or capacity for manual 384-well processing), ability to assemble indexed Tn5 transposomes in-house, input nuclei amounts sufficient for bulk tagmentation and sorting, and target experiments of up to ~10,000 cells per run; compatible with semi-automated 384-well workflows and benchmarking against common scATAC datasets.
Fails when: Fails or is impractical when no FANS or liquid-handling automation is available or when in-house Tn5 assembly is not possible; performance and annotation accuracy are unvalidated for many tissues, rare PBMC sub-subtypes, and clinical samples; barcode collision and doublet rates may increase with higher multiplexing or inadequate barcode diversity; cost-effectiveness is reduced when capital equipment and labor costs are included or unavailable.
