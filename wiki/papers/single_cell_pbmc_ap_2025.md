---
paper_id: single_cell_pbmc_ap_2025
title: "Single-Cell Transcriptomic Atlas of Peripheral Blood Reveals B-Cell-Driven Signature Predictive of Acute Pancreatitis Severity."
doi: "10.1002/mco2.70350"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12434316/"
source_ids: {doc_id: "pmc:12434316", pmid: "40959459", pmcid: "12434316", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_cell_type_annotation", "rna_clustering", "rna_differential_expression"]
retrieval_goals: ["prior_findings"]
retrieval_intents: ["Find a PBMC atlas or review listing canonical marker genes per major immune cell type and subsets."]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
Generated an integrated PBMC single-cell RNA-seq atlas (102,042 cells) with paired scTCR/scBCR from acute pancreatitis (AP) patients across days 1, 3 and 7, identified expansion of MZB1+ plasma cells associated with complicated AP and recovery, validated plasma-cell markers and altered serum immunoglobulins/cytokines in independent cohorts and mouse models, and derived a nine-gene B-cell transcriptomic signature that predicted persistent organ failure with AUROC >0.95 in internal validation and retained accuracy in two external cohorts.

## Hypothesis framed
Expansion of MZB1+ plasma cells in peripheral blood underlies severity in acute pancreatitis, and a B-cell–derived nine-gene blood transcriptomic signature can predict persistent organ failure early in the clinical course.

## Questions answered
- Can a B-cell-derived blood transcriptomic signature predict acute pancreatitis severity and persistent organ failure earlier than standard clinical scores?
- Are MZB1-expressing plasma cells expanded in complicated AP and do their dynamics correlate with clinical course and serum immunoglobulin changes?
- Which PBMC cell types and marker genes are detectable in AP patients at single-cell resolution (days 1, 3, 7)?

## Key findings
Produced a PBMC scRNA-seq atlas of 102,042 cells annotated into 12 immune cell types; observed marked inter-patient heterogeneity but a distinct expansion of MZB1+ plasma cells in complicated AP that tracked recovery and paralleled serum IgA changes; validated plasma-cell markers in an independent cohort (n=14) and altered serum immunoglobulin/cytokine profiles (n=32) and in mouse AP models; derived a nine-gene B-cell signature (S100A8, DUSP1, JUN, HBA2, FOS, CYBA, JUNB, S100A9, WDR83OS) that predicted AP severity/persistent organ failure with AUROC >0.95 in internal validation (n=114), and retained predictive accuracy in external AP cohort (n=87) and AP + non-AP sepsis cohort (n=174), outperforming standard clinical scoring systems in their tests.

## Methods used
Integrated single-cell RNA-seq with paired scTCR and scBCR profiling on PBMCs; clustering and manual/marker-based cell type annotation into 12 immune types; differential expression analyses; cell–cell interaction inference; trajectory analysis; construction and training of a nine-gene predictive classifier (B-cell-derived) with internal (n=114) and external (n=87; n=174) validation; serum immunoglobulin and cytokine assays in validation cohorts; mouse AP model experiments for mechanistic validation.

## Method and dataset
scRNA-seq + scTCR/scBCR on peripheral blood mononuclear cells from 7 AP patients (4 complicated, 3 uncomplicated) and 2 healthy controls, sampled at days 1, 3, 7 after admission; 102,042 cells after QC; downstream analyses included clustering, annotation (12 immune cell types), differential expression, trajectory and cell–cell interaction analyses. Signature model derived from B-cell transcripts and trained/validated on bulk/transcriptomic blood cohorts (internal n=114; external n=87 AP; external n=174 AP+non-AP sepsis). Assumes comparable blood sample processing, capture of B/plasma cells, and similar clinical endpoint definitions (persistent organ failure).

## Limitations
Small discovery single-cell cohort (n=7) limits statistical power and generalizability; high internal AUROC suggests risk of overfitting despite external validation; observational design prevents causal inference about MZB1+ plasma cells; heterogeneous patient trajectories may limit robustness; assay/processing standardization and prospective multicenter validation are required before clinical translation.

## Evidence pattern
Entity definition (defined 12 immune cell types and marker genes from PBMC scRNA-seq), statistical_unit both at cell-level (102,042 cells) and patient-level (discovery n=7; internal validation n=114; external n=87 and n=174), comparison design (complicated vs uncomplicated AP across days 1/3/7), metrics (AUROC for classifier), analyses used (clustering, differential expression, trajectory, cell–cell interaction, scTCR/scBCR linking), and validation (independent human cohorts, serum assays, mouse models).

## Extends or contradicts
Extends prior PBMC/immune-response single-cell atlases by providing AP-focused scRNA-seq data and a B-cell-derived prognostic signature; does not directly contradict the existing listed single-cell methodology or integration benchmarking papers in the wiki.

## Boundary conditions
Works when: Applied to peripheral blood/PBMC transcriptomes sampled early in AP (within first day(s) of admission; discovery samples collected days 1, 3, 7), when B cells/plasma cells are adequately captured (single-cell datasets totaling ~100k cells or bulk PBMC/blood RNA cohorts of size comparable to validations: ≥80 samples), and when clinical endpoint is persistent organ failure defined similarly to this study.
Fails when: Will likely fail or be unreliable when used on non-blood tissues (e.g., pancreas tissue), in datasets lacking B-cell/plasma-cell capture or with very low B-cell counts (<~1% of cells), on samples collected late in disease course (>48–72 hours post-admission) without adjustment, in small cohorts (<<50 samples) where overfitting risk is high, or without standardized sample processing and endpoint definitions.
