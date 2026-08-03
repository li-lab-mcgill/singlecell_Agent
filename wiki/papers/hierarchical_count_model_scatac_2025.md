---
paper_id: hierarchical_count_model_scatac_2025
title: "A hierarchical, count-based model highlights challenges in scATAC-seq data analysis and points to opportunities to extract finer-resolution information."
doi: "10.1186/s13059-025-03735-y"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12442292/"
source_ids: {doc_id: "pmc:12442292", pmid: "40963104", pmcid: "12442292", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_clustering", "atac_cell_type_annotation", "atac_differential_accessibility"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["What is the recommended preprocessing for scATAC-seq to mitigate depth bias for joint embedding (TF-IDF followed by LSI), and what failure modes or assumptions are known?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
The paper introduces a hierarchical count model motivated by the scATAC-seq data-generating process and uses simulations plus adapted bulk-normalization tests (e.g., smooth GC-FQ) to evaluate limits of per-cell, per-region inference. It finds that current scATAC-seq datasets are too sparse for reliable locus-level single-cell accessibility calls, that normalization remains challenging, and that aggregation to pseudobulk yields more robust signals while quantitative information in the counts suggests potential for finer resolution if assay sensitivity improves.

## Hypothesis framed
Current scATAC-seq data and existing normalization/transformation methods are insufficient to reliably infer true single-cell, single-region chromatin accessibility states; a hierarchical count model can quantify these limits and inform preprocessing/aggregation strategies.

## Questions answered
- Can current scATAC-seq datasets reliably infer per-cell, per-region binary or ternary chromatin accessibility states?
- Do bulk-derived normalization methods (e.g., smooth GC-FQ) and single-cell level normalization recover locus-level accessibility in single cells, or is aggregation/pseudobulk required for robust signals?
- How do sequencing depth variation, sparsity, and region-specific biases limit inference of per-cell, per-region accessibility?

## Key findings
Simulations and normalization tests indicate that current scATAC-seq datasets—characterized by high sparsity and sequencing-depth variation—are generally too sparse to reliably recover true per-cell, per-region accessibility states. Bulk-derived normalization adaptations (e.g., smooth GC-FQ) have limited ability to recover locus-level states at single-cell resolution, while aggregation to cell-type or pseudobulk levels produces robust, interpretable accessibility signals. The underlying scATAC-seq counts retain quantitative biological signals (e.g., reflecting nucleosome turnover), implying that improved assay sensitivity could enable finer-resolution inference.

## Methods used
Developed a hierarchical count model of scATAC-seq data-generating process; simulation experiments varying sparsity, sequencing depth, and region-specific effects; adapted bulk ATAC-seq normalization code (Van den Berge et al.) including smooth GC-FQ applied to single-cell and pseudobulk counts; comparative analyses contrasting binary/ternary vs quantitative accessibility assumptions; evaluation of normalization and aggregation impacts on downstream interpretation.

## Method and dataset
Methods: hierarchical generative count model and simulation studies; normalization tests adapting bulk smooth GC-FQ to single-cell and pseudobulk counts. Data: simulated scATAC-seq count matrices with controlled sparsity, sequencing depth, and region-specific biases; normalization applied to both simulated single-cell and aggregated pseudobulk counts. Assumptions: model assumes a specific data-generating process for scATAC (counts reflect accessibility modulated by sequencing depth and region effects), and treats accessibility conceptualizations as binary/ternary or quantitative in different scenarios.

## Limitations
Conclusions are primarily simulation-based and rely on the model's assumptions about the scATAC-seq data-generating process; no new experimental assays or increased-sensitivity datasets were generated, so the study cannot quantify how much sensitivity improvement is required. Bulk-derived normalization methods may not be optimal for single-cell counts, not all region- or cell-specific biases were exhaustively characterized, and specific preprocessing pipelines (e.g., TF-IDF+LSI) were not explicitly evaluated or parameterized.

## Evidence pattern
entity_definition, comparison_design, statistical_unit, validation, boundary_conditions, effect_metric

## Extends or contradicts
Extends prior bulk ATAC-seq normalization approaches (e.g., Van den Berge et al.) by adapting them to single-cell and pseudobulk contexts; contradicts or qualifies claims that current scATAC-seq data fully resolves chromatin accessibility at single-cell, single-locus resolution.

## Boundary conditions
Works when: Applies when datasets exhibit the high sparsity and sequencing-depth variation typical of contemporary scATAC-seq experiments and when analyses aggregate counts to cell-type or pseudobulk levels; the hierarchical count model and simulations are informative under assumed data-generating processes that include region-specific biases and per-cell depth variation.
Fails when: Findings do not hold when assay sensitivity and per-cell coverage substantially increase such that per-cell, per-region counts are dense enough to observe true locus-level accessibility; results may fail if the actual scATAC-seq data-generating process substantially deviates from the model assumptions or when region- or cell-specific biases not modeled here dominate the signal. Bulk-derived normalization adaptations may fail when applied directly to raw single-cell counts without accounting for unique single-cell count properties.
