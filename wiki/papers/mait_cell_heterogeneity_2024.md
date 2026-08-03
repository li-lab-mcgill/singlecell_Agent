---
paper_id: mait_cell_heterogeneity_2024
title: "MAIT cell heterogeneity across paired human tissues reveals specialization of distinct regulatory and enhanced effector profiles."
doi: "10.1126/sciimmunol.adn2362"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12743559/"
source_ids: {doc_id: "pmc:12743559", pmid: "39241054", pmcid: "12743559", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_cell_type_annotation", "rna_clustering", "rna_differential_expression"]
retrieval_goals: ["broad_background"]
retrieval_intents: ["Define MAIT cell RNA markers and expected chromatin/motif features in PBMC"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
This study profiles human MAIT cells across donor‑matched blood, barrier and lymphoid tissues from 18 deceased organ donors using MR1 tetramer staining, flow cytometry, single‑cell CITE‑seq and scTCR‑seq to define tissue‑adapted MAIT subsets. It reveals two major tissue‑adapted programs — an intestinal CD103+ CD39high CD27low immunoregulatory phenotype and a hepatic NCAM1/CD56+ enhanced‑effector phenotype with restricted TCR breadth and higher MR1 binding — demonstrating site-specific functional specialization.

## Hypothesis framed
Human MAIT cells exhibit tissue-specific residency programs and functional specialization such that gut-resident MAITs adopt an immunoregulatory phenotype while liver-resident MAITs adopt an enhanced effector phenotype with distinct transcriptional and TCR features.

## Questions answered
- Do MAIT cells exhibit tissue-specific phenotypes and residency adaptations across matched human organs?
- Are liver MAIT cells enriched for an NCAM1/CD56+ subset with higher effector magnitude, polyfunctionality, elevated MR1 binding, and reduced TCR repertoire breadth compared with other tissues?
- Are intestinal MAIT cells enriched for CD103+ CD39high CD27low regulatory phenotypes and do CD56 and CD39 subsets accumulate with donor age?

## Key findings
MAIT cells were detected in all sampled sites and were highly enriched in liver (mean ~15.7% of T cells). Two dominant tissue adaptations were identified: (1) intestinal CD103+ resident MAITs with CD39high and CD27low immunoregulatory profile; (2) hepatic NCAM1/CD56+ MAITs that dominate the liver, show increased response magnitude and polyfunctionality, have reduced TCR repertoire breadth, elevated MR1 tetramer binding, and transcriptional skewing toward innate activation pathways. Both the intestinal CD39high and hepatic CD56+ subsets increased with donor age. CD56 expression was inducible by antigen or IL-7 and reached a persistent steady-state after exposure. MAIT cells were defined consistently as MR1-5-OP-RU tetramer+ Vα7.2+ CD161+.

## Methods used
Matched organ sampling from 18 deceased donors; MR1-5-OP-RU tetramer staining; multicolor flow cytometry and protein phenotyping; secretome/functional assays to measure response magnitude and polyfunctionality; single-cell CITE-seq (scRNA + surface protein) and scTCR-seq for transcriptional programs and TCR repertoire; in vitro antigen and IL-7 stimulation assays to test CD56 induction; donor clinical metadata and serologies recorded.

## Method and dataset
Single-cell CITE-seq and scTCR-seq plus multicolor flow cytometry and functional assays on matched blood, spleen, liver, ileum, caecum, colon, lung, skin and adjacent lymph nodes from 18 deceased organ donors (mean age 60). MAIT cells defined as MR1-5-OP-RU tetramer+ Vα7.2+ CD161+. Analyses included clustering, cell-type annotation, differential abundance across tissues, transcriptional signature derivation, TCR repertoire breadth estimation, MR1-binding quantification, and stimulation experiments. Assumptions: cross-sectional single timepoint from deceased donors reflects steady-state tissue-adapted phenotypes; MR1 tetramer reliably identifies MAIT cells.

## Limitations
Cross-sectional study of deceased organ donors (n=18) introduces possible confounding from terminal illness, peri-mortem interval, medications, and heterogeneous comorbidities; single timepoint sampling prevents causal or longitudinal inference; modest cohort size limits power for some comparisons; no chromatin accessibility (ATAC-seq) or motif enrichment data were generated; results may not generalize to living donors, pediatric populations, or acute infection contexts.

## Evidence pattern
entity_definition, comparison_design, statistical_unit, effect_metric, controls_covariates, validation, boundary_conditions

## Extends or contradicts
Extends prior descriptions of circulating/blood MAIT cells by demonstrating tissue-specific residency programs and functional specialization across multiple matched human organs (gut regulatory CD39high CD103+ and liver effector CD56+ programs).

## Boundary conditions
Works when: Applied to donor-matched human tissues sampled post-mortem from adult donors (here n=18, mean age 60) where MAIT cells are identified as MR1-5-OP-RU tetramer+ Vα7.2+ CD161+; when analyses combine scRNA (CITE-seq) with surface protein measurements, flow cytometry validation, and scTCR-seq for repertoire analyses; when assessing steady-state tissue adaptations rather than acute/longitudinal responses.
Fails when: Findings may not apply to PBMC-only datasets without tissue samples or MR1 tetramer staining, to live longitudinal sampling where dynamics differ from post-mortem steady-state, to pediatric or non-human cohorts, in settings with active systemic infection or recent treatments that alter MAIT phenotype, or when chromatin accessibility/motif information is required (no ATAC/motif data were generated).
