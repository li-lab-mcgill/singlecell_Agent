---
paper_id: single_cell_de_nested_2025
title: "Single-cell differential expression analysis between conditions within nested settings."
doi: "10.1093/bib/bbaf397"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12343076/"
source_ids: {doc_id: "pmc:12343076", pmid: "40794957", pmcid: "12343076", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_differential_expression", "multi_batch_correction"]
retrieval_goals: ["broad_background"]
retrieval_intents: ["What statistical guidance establishes that donors/samples, not cells, are the valid replication unit for inference (to avoid pseudoreplication) in single-cell RNA/ATAC studies?"]
extends: ["benchmarking_ds_multisubject_2022"]
added: 2026-05-15
session: unknown
---

## Summary
This paper benchmarks seven differential expression methods plus an adapted hierarchical bootstrap on simulated and one real single-cell RNA-seq dataset in nested (donor/sample → cell) and atlas (multi-batch) settings, quantifying accuracy (AUPRC), FDR calibration, and runtime trade-offs. It shows that pseudobulk aggregation to donor/sample (DESeq2) outperforms or matches single-cell–level methods for single-dataset analyses, while permutation and DREAM perform better at atlas-scale with runtime trade-offs.

## Hypothesis framed
Aggregating single-cell RNA-seq to donor/sample (pseudobulk) provides equal or superior differential expression accuracy and better practical runtime trade-offs compared to single-cell–level DE methods in single-dataset settings, while atlas-level analyses require different trade-offs (permutation best quality, DREAM practical).

## Questions answered
- Do pseudobulk methods outperform single-cell–level DE methods for dataset-level single-cell RNA-seq differential expression?
- Which DE methods control FDR and perform best in atlas (multi-batch) nested settings, considering runtime trade-offs?
- How do different methods compare on precision-recall (AUPRC) and FDR calibration across nested simulation scenarios?

## Key findings
1) Single-dataset simulations: DESeq2 (pseudobulk) achieved mean AUPRC = 0.93, scVI 0.87, other methods 0.71–0.81. 2) Atlas (multi-batch) simulations: permutation test highest AUPRC = 0.78 but poor runtime; DREAM, DESeq2, hierarchical bootstrap, and MAST AUPRC = 0.73–0.77; scVI and t-test AUPRC ≈ 0.66–0.68. 3) FDR calibration: DREAM and permutation matched nominal FDR in simulations; DESeq2 and MAST slightly exceeded nominal FDR at small p-values; scVI was conservative for p<0.03 but exceeded nominal FDR at larger cutoffs; hierarchical bootstrap exceeded nominal FDR across cutoffs. 4) Methods developed specifically for single-cell analysis did not outperform pseudobulk methods on dataset-level DE and often required substantially longer runtimes; distinct produced near-minimal p-values and was excluded from some benchmarks.

## Methods used
Benchmarked DESeq2, MAST, DREAM, scVI, permutation test, distinct, t-test, and an adapted hierarchical bootstrap across four simulated scenarios (Dataset, Atlas, varying cell numbers, unbalanced conditions) plus one real dataset; 20 independent simulations per scenario; evaluated AUPRC, negative-control FDR calibration (compare nominal p-value cutoffs to observed FDR), and runtimes.

## Method and dataset
Applied statistical and ML DE methods to single-cell RNA-seq data simulated under nested donor/sample→cell hierarchies and one real single-cell RNA-seq dataset; simulations used fewer cells than many real studies (exact counts not specified), modeled multi-batch (atlas) and single-dataset designs, and unbalanced cell counts. Key implicit assumptions tested: common DE methods assume cell-level independence (violated when cells are pseudoreplicates) while pseudobulk aggregates per donor/sample assuming donors/samples are independent replication units.

## Limitations
Simulations used fewer cells than many real single-cell studies, limiting scalability assessment; some methods hit practical upper limits preventing full cell-number exploration; did not exhaustively explore performance as batch count increases to very large numbers; hierarchical bootstrap showed FDR control problems and needs refinement; focused on RNA-seq (not ATAC); did not provide formal theoretical proofs or required donor/sample counts for power.

## Evidence pattern
entity_definition, statistical_unit, comparison_design, effect_metric, validation, boundary_conditions

## Extends or contradicts
Extends prior multi-subject single-cell DE benchmarking (benchmarking_ds_multisubject_2022) and contradicts claims that single-cell–level methods consistently outperform pseudobulk approaches for dataset-level DE.

## Boundary conditions
Works when: Works when: dataset-level (single-batch or per-dataset) DE analyses with donor/sample as replication unit and cells aggregated to pseudobulk — in simulations DESeq2 achieved mean AUPRC = 0.93. For atlas-level (multi-batch) analysis, permutation tests provided highest accuracy (AUPRC = 0.78) but at high runtime; DREAM provided a practical compromise with AUPRC in the 0.73–0.77 range.
Fails when: Fails or underperforms when: applied at atlas-scale with many batches where runtimes become limiting (permutation tests slow); hierarchical bootstrap exhibited inflated FDR across cutoffs in these simulations; scVI shows nonmonotonic FDR behavior (conservative at p<0.03 then exceeding nominal FDR at larger cutoffs); some methods reached practical upper limits as cell numbers increase; distinct returned near-minimal p-values and was unusable in parts of the benchmark.
