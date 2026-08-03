---
paper_id: joint_cis_reg_networks_multitissue
title: "Joint reconstruction of cis-regulatory interaction networks across multiple tissues using single-cell chromatin accessibility data."
doi: "10.1093/bib/bbaa120"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC8138825/"
source_ids: {doc_id: "pmc:8138825", pmid: "32578841", pmcid: "8138825", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_grn_inference", "multi_grn_inference"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Identify canonical method papers for co-accessibility and extract assumptions, controls, and validations"]
extends: []
added: 2026-05-27
session: unknown
---

## Summary
Introduces JRIM, a joint framework to reconstruct and compare cis-regulatory interaction networks across multiple tissues from single-cell ATAC-seq by leveraging co-accessibility with coordinated sparsity control. Applied to ~80,000 cells from 13 mouse tissues, JRIM yields more balanced, comparable networks than single-tissue methods and reveals common and tissue-specific regulatory interactions linked to function.

## Background
Most co-accessibility methods infer cis-regulatory networks per cell type or tissue independently, leading to networks with inconsistent sparsity and noise when cell numbers vary, which hinders cross-tissue comparison. A joint approach is needed to control sparsity across tissues, capture shared interactions, and highlight tissue-specific regulation from single-cell chromatin accessibility.

## Method and dataset
JRIM jointly estimates co-accessibility-based cis-regulatory interaction maps across multiple tissues, enforcing coordinated sparsity to reduce uncorrelated technical noise and enable direct comparability. Assumptions: co-accessibility proxies cis-regulatory interactions; joint sparsity improves comparability without masking true shared edges; distance-aware modeling respects genomic proximity. Data: single-cell ATAC-seq (~80,000 cells) across 13 adult mouse tissues (one sample per tissue), 436,206 peaks (MACS2). Complementary data included scRNA-seq (11 tissues), ChIP-seq for H3K4me1, H3K4me3, H3K27ac and CTCF (up to 10 tissues), TBX3 ChIP-seq in heart, housekeeping and tissue-specific gene sets, and locus-specific 4C-seq.

## Analysis
Constructed joint co-accessibility networks per tissue with coordinated sparsity; compared JRIM to Cicero for balance and cross-tissue comparability (e.g., fraction of edges unique to a single tissue). Assessed genomic distance decay of interaction frequency; evaluated enrichment/depletion of interactions across genomic annotations (promoter, 5' UTR, intronic, intergenic); quantified cross-tissue conservation by annotation class. Linked interactions to gene sets (housekeeping, tissue-specific) and differential expression. Integrated histone mark and TF ChIP-seq overlap to support tissue-specific interactions, including TBX3 in heart. Performed locus-level validation at the Gys2 region using 4C-seq contact frequency and histone mark profiles.

## Key findings
JRIM reconstructed on average ~2.28 million interactions per tissue (range ~1.28–3.38 million), producing more balanced, comparable networks than Cicero and reducing the fraction of edges detected in only one tissue. Interaction frequency decayed with genomic distance and was enriched at promoters and 5' UTRs while depleted in intronic/intergenic regions; promoter/5' UTR-associated interactions showed highest cross-tissue conservation, whereas distal elements were more tissue-specific. Common interactions across 13 tissues were linked to housekeeping functions; tissue-specific networks aligned with tissue-relevant functions and differentially expressed genes. Tissue-specific interactions were supported by coordinated histone modifications and tissue-relevant TFs (e.g., TBX3 in heart). A kidney-specific long-range enhancer–promoter interaction downstream of Gys2 predicted by JRIM was supported by increased 4C-seq contact frequency and consistent histone mark profiles.

## Limitations
Only one sample per tissue with variable cell numbers may affect comparability and sensitivity. Co-accessibility infers rather than directly measures physical contacts; experimental validation was limited to reanalysis of existing datasets (e.g., locus-specific 4C-seq). ChIP/TF data were unavailable for all tissues, potentially biasing integrative support. Tissue-level aggregation may obscure within-tissue cell-type heterogeneity. Joint sparsity control may smooth true tissue-unique interactions. Results depend on peak calling and preprocessing choices.

## Metrics used
Number of reconstructed interactions per tissue; fraction of edges unique to a single tissue; genomic distance decay of interaction frequency; enrichment/depletion across genomic annotations; cross-tissue conservation rates by annotation class; functional enrichment of housekeeping and tissue-specific gene sets; overlap with histone mark and TF ChIP-seq peaks; 4C-seq contact frequency at the Gys2 locus.
