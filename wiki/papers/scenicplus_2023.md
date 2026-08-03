---
paper_id: scenicplus_2023
title: "SCENIC+: single-cell multiomic inference of enhancers and gene regulatory networks."
doi: "10.1038/s41592-023-01938-4"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC10482700/"
source_ids: {doc_id: "pmc:10482700", pmid: "37443338", pmcid: "10482700", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multi_grn_inference", "atac_peak_to_gene", "atac_motif_analysis"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Determine computational method classes and failure modes for inferring transcription factor programs from single-cell ATAC or paired RNA+ATAC multiome data in cell-type-specific disease analyses."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
SCENIC+ is a computational framework for inferring enhancer-driven gene regulatory networks from single-cell chromatin accessibility, gene expression, and DNA motif information. It predicts candidate enhancers, links enhancers to target genes, and nominates upstream transcription factors, enabling cell-type-specific regulatory-network analysis across multiomic datasets.

## Hypothesis framed
Enhancer-driven gene regulatory networks can be inferred from joint single-cell chromatin accessibility and gene expression data by combining accessible-region modeling, motif enrichment, enhancer-gene linking, and transcription-factor-to-target-gene relationships.

## Questions answered
- Can joint single-cell RNA and chromatin accessibility data be used to infer transcription factor-enhancer-target gene regulatory networks?
- Do topic modeling, motif enrichment, and a curated motif database with multiple motifs per transcription factor improve transcription factor identification compared with simpler motif scanning approaches?
- Can SCENIC+ recover cell-type-specific and cross-species conserved regulatory programs in datasets such as PBMCs, ENCODE cell lines, melanoma cell states, Drosophila retinal development, and human-mouse cerebral cortex?

## Key findings
SCENIC+ inferred cell-type-specific enhancer-driven regulatory networks across human PBMCs, ENCODE cell lines, melanoma cell states, Drosophila retinal development, and cerebral cortex cross-species comparisons. The study concluded that topic modeling helped prioritize informative accessible regions, using multiple motifs per transcription factor and a motif collection of more than 30,000 motifs improved recall for relevant transcription factors, and motif enrichment reduced false-positive predictions relative to simple motif scanning.

## Methods used
SCENIC+ integrates single-cell chromatin accessibility, gene expression, and DNA sequence motif data; identifies candidate cis-regulatory elements; links candidate enhancers to genes; performs motif enrichment to nominate upstream transcription factors; uses a curated and clustered motif collection containing more than 30,000 motifs; and benchmarks predictions against CellOracle, Pando, FigR, GRaNIE, and SCENIC using AUCell-based enrichment scores, dimensionality reduction, Leiden clustering, and adjusted Rand index comparisons to cell-type labels.

## Method and dataset
The method was applied to single-cell multiomic or paired chromatin accessibility and gene expression data from human peripheral blood mononuclear cells, ENCODE cell lines, melanoma cell states, Drosophila retinal development, and human-mouse cerebral cortex comparisons. Dataset sizes are not specified in the summary. The method assumes usable chromatin accessibility profiles, matched or integrated gene expression measurements, genome annotations, and motif databases that contain motifs relevant to the transcription factors under study.

## Limitations
Predicted transcription factor-enhancer-gene links are computational predictions and require experimental validation. Motif-based inference may not distinguish closely related transcription factors with similar binding motifs. Enhancer-gene links inferred from accessibility-expression associations do not establish direct causality. Accuracy depends on single-cell multiome data quality, chromatin accessibility coverage, genome annotations, motif database coverage, and may degrade in sparse or noisy datasets or in species, tissues, and developmental contexts with poorer annotations.

## Evidence pattern
The study used entity definition for SCENIC+ regulatory units, comparison design against CellOracle, Pando, FigR, GRaNIE, and SCENIC, AUCell-based enrichment scores, dimensionality reduction, Leiden clustering, adjusted Rand index comparisons to cell-type labels, validation across multiple biological systems and species, and boundary-condition analysis emphasizing motif ambiguity, annotation dependence, and correlation-based enhancer-gene links.

## Extends or contradicts
SCENIC+ extends prior regulon and gene regulatory network inference approaches such as SCENIC by explicitly adding candidate cis-regulatory elements and enhancer-to-gene links to transcription factor-target gene networks. It does not contradict a specific prior paper in the provided wiki list.

## Boundary conditions
Works when: Works when joint or integrable single-cell chromatin accessibility and gene expression data are available, accessible regions can be mapped to a reference genome, motif databases contain relevant transcription factor motifs, and cell states have enough signal to support motif enrichment and accessibility-expression association analyses.
Fails when: Fails or becomes unreliable when chromatin accessibility data are sparse or noisy, genome annotations or motif databases are incomplete, transcription factors share highly similar motifs, enhancer-gene associations are confounded by correlation rather than direct regulation, or the biological context lacks sufficient matched expression and accessibility information for cell-type-specific inference.
