---
paper_id: sensitive_cluster_free_2023
title: "Sensitive cluster-free differential expression testing."
doi: "10.1101/2023.03.08.531744"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC10028920/"
source_ids: {doc_id: "pmc:10028920", pmid: "36945506", pmcid: "10028920", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_differential_expression"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Determine how single-cell disease-control studies statistically test cell-type/state abundance and avoid confounding molecular differential state claims with compositional shifts and donor/batch covariates."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This paper introduces miloDE, a cluster-free differential expression framework for single-cell RNA-seq that tests expression changes within overlapping graph neighbourhoods rather than within discrete clusters or annotated cell types. It matters because cluster-level differential expression can miss localized, rare, or continuous transcriptional changes and can make results dependent on annotation granularity.

## Hypothesis framed
Differential expression testing over overlapping graph neighbourhoods in a latent single-cell embedding can detect condition-associated transcriptional changes more sensitively and specifically than testing only within predefined clusters or cell-type annotations.

## Questions answered
- Can single-cell RNA-seq differential expression be tested without first assigning cells to discrete clusters or cell types?
- Does graph-neighbourhood differential expression improve detection of localized or continuous transcriptional changes compared with cluster-based testing?
- How do latent embedding choice, graph construction, neighbourhood assignment, statistical testing, and multiple-testing correction affect neighbourhood-level differential expression?

## Key findings
miloDE detected differential expression without requiring cell clustering or cell-type annotation and supported localized differential expression testing across overlapping graph neighbourhoods. In real scRNA-seq data, it identified a transient haemogenic endothelium-like state in chimeric mouse embryos lacking Tal1 and revealed distinct transcriptional programs associated with macrophage changes in patients with idiopathic pulmonary fibrosis. The summary reports no numerical sensitivity, specificity, sample-size, or effect-size values.

## Methods used
The method constructs a graph from a latent embedding of single-cell RNA-seq data, selects index cells, defines overlapping neighbourhoods from each index cell and nearby cells, and performs differential expression testing within each neighbourhood. The paper evaluates graph construction, neighbourhood assignment, statistical testing, multiple-testing correction, and embedding choices using simulations and real scRNA-seq datasets.

## Method and dataset
miloDE was applied to single-cell RNA-seq simulations and real datasets including mouse gastrulation/chimeric Tal1 mutant embryo data and macrophage data from idiopathic pulmonary fibrosis patients. Dataset sizes are not specified in the summary. The method assumes that the latent embedding preserves biologically relevant local transcriptional structure, that graph neighbourhoods contain sufficiently homogeneous nearby cells, and that enough cells and biological replicates are available for reliable neighbourhood-level testing and complex experimental design modeling.

## Limitations
miloDE still groups cells into neighbourhoods, so it retains limitations of cell-group-based differential expression. Performance depends on latent embedding quality, integration strategy, graph construction, neighbourhood size, and the number of cells and biological replicates. Rare populations can remain difficult when neighbourhoods contain too few cells or are mixed with transcriptionally similar abundant populations. Inappropriate embeddings may obscure or exaggerate biologically meaningful condition effects.

## Evidence pattern
Entity definition of miloDE; comparison design against cluster-based differential expression; statistical unit defined as overlapping graph neighbourhoods; analysis of graph construction, neighbourhood assignment, statistical testing, and multiple-testing correction; validation using simulations and real scRNA-seq datasets; discussion of covariates and complex experimental designs; boundary-condition analysis around embedding choice, neighbourhood size, rare populations, and replicate availability.

## Extends or contradicts
The paper extends the Milo graph-neighbourhood concept from differential cell abundance testing to differential expression testing. It challenges the standard cluster-then-test single-cell differential expression workflow by showing that differential expression can be tested directly over overlapping neighbourhoods instead of discrete cell types or clusters.

## Boundary conditions
Works when: Works when single-cell RNA-seq data can be represented in a latent embedding whose local graph structure captures relevant biological states, when neighbourhoods contain enough similar cells for expression testing, and when the experimental design includes sufficient biological replicates for condition and covariate modeling. It is especially suited to localized, rare, subtle, or continuous transcriptional states where discrete clustering may be too coarse.
Fails when: May fail or lose power when the embedding removes condition-specific variation, when graph neighbourhoods are too small, too heterogeneous, or dominated by transcriptionally similar abundant cells, when rare populations have too few cells, or when there are too few biological replicates for reliable differential expression testing. It is not a compositional abundance model and does not directly solve separation of cell-state abundance shifts from molecular differential state claims.
