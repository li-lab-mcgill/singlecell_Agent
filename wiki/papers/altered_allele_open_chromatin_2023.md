---
paper_id: altered_allele_open_chromatin_2023
title: "Altered and allele-specific open chromatin landscape reveals epigenetic and genetic regulators of innate immunity in COVID-19."
doi: "10.1016/j.xgen.2022.100232"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9715265/"
source_ids: {doc_id: "pmc:9715265", pmid: "36474914", pmcid: "9715265", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_differential_accessibility", "atac_motif_analysis", "multiomic_integration"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["What PBMC biological validation patterns were used in GLUE or similar RNA+ATAC co-embedding papers?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
Integrated single-cell RNA, single-cell ATAC, and genotype analysis of peripheral blood mononuclear cells from hospitalized and convalescent COVID-19 patients identified classical monocytes as the main cell type with COVID-associated chromatin and transcriptional changes, discovered C/EBP-driven regulatory programs and a functional lncRNA regulator LUCAT1, and detected allele-specific open chromatin variants (notably rs6800484-C) linked to lower CCR2 expression and higher hospitalization risk.

## Hypothesis framed
Differential chromatin accessibility and allele-specific open chromatin in peripheral blood monocytes underlie transcriptional programs that contribute to COVID-19 severity, and integrated single-cell RNA+ATAC with genotype data can identify the key genetic and epigenetic regulators.

## Questions answered
- Which PBMC cell types exhibit the strongest COVID-19-associated transcriptional and chromatin accessibility changes?
- Do allele-specific open chromatin (ASoC) variants link to gene expression changes and COVID-19 GWAS signals in PBMCs?
- Does the long noncoding RNA LUCAT1 modulate C/EBP-driven transcriptional programs in classical monocytes?

## Key findings
1) Classical monocytes showed the strongest COVID-19-associated transcriptional and chromatin accessibility changes across the cohort. 2) Differences between mild and severe hospitalized patients represented differences in response magnitude rather than distinct transcriptional programs. 3) Motif enrichment and subclustering implicated C/EBP family transcription factors as condition-specific regulators in classical monocytes. 4) LUCAT1 was identified as a regulator interacting with C/EBP TFs; loss-of-function experiments supported its role in modulating immune gene expression. 5) Multiple allele-specific open chromatin SNPs were detected in hospitalized patients; rs6800484-C exhibited reduced chromatin accessibility, associated with lower CCR2 expression in classical monocytes, and with increased risk of COVID-19 hospitalization.

## Methods used
Single-cell RNA-seq, single-cell ATAC-seq, genotype arrays; cell-type annotation; differential expression analysis; differential accessibility peak calling (DAPs); subclustering of classical monocytes; transcription factor motif-enrichment analysis; integration of accessibility and gene expression to nominate peak-to-gene links; allele-specific open chromatin (ASoC) analysis intersected with eQTLs and COVID-19 GWAS; loss-of-function (functional) experiments for LUCAT1 validation.

## Method and dataset
Applied integrative analyses (scRNA-seq + scATAC-seq + genotype) on peripheral blood mononuclear cells from 48 individuals (46 hospitalized samples, 32 convalescent samples, 20 longitudinal samples). scRNA and scATAC data were analyzed for cell-type annotation, differential expression, and differential accessibility; genotype arrays were used to call ASoC in heterozygous individuals and intersect with eQTL/GWAS. Assumptions: adequate per-cell-type cell counts for statistical testing, presence of heterozygous carriers for ASoC detection, and that bulk-like peak-to-gene correlation across single cells reflects regulatory links. (The summary does not specify whether modalities were profiled in the same single cells or separately.)

## Limitations
Only peripheral blood profiled (no tissue-resident immune cells such as lung). Moderate and heterogeneous cohort (variable treatments and comorbidities) limiting power and generalizability. ASoC and expression associations are correlative; causal effects beyond CCR2 not established in vivo. Experimental validation was focused on LUCAT1 and select targets rather than genome-wide functional follow-up. The summary does not state whether RNA and ATAC were measured in the same cells (multiome) or how modality matching was handled.

## Evidence pattern
entity_definition, comparison_design, statistical_unit, effect_metric, validation, boundary_conditions

## Extends or contradicts
Extends prior observations of innate immune dysregulation and epigenetic changes in COVID-19 (see epigenetic_memory_coronavirus_2023) by linking cell-type-specific chromatin accessibility and allele-specific variation to transcriptional programs and a hospitalization-associated SNP (rs6800484-C) affecting CCR2.

## Boundary conditions
Works when: Works when: PBMCs are profiled with both scRNA-seq and scATAC-seq and sample-level genotypes are available; cohort includes hospitalized and convalescent individuals (similar scale: ~48 individuals, 46 hospitalized samples, 32 convalescent samples, 20 longitudinal samples); sufficient numbers of classical monocytes and heterozygous individuals for ASoC detection; differential chromatin accessibility is present and detectable with DAP analyses.
Fails when: Fails when: only tissue-resident immune cells are of interest (lung, tissue not sampled here); no genotype data or insufficient heterozygosity prevents ASoC analysis; scATAC or scRNA modalities are missing or have very low cell counts per cell type (insufficient power to detect DAPs or ASoC); cohort too small or too heterogeneous to robustly detect condition-specific chromatin or expression changes.
