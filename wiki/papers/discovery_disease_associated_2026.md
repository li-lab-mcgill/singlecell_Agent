---
paper_id: discovery_disease_associated_2026
title: "Discovery of disease-associated cellular states using ResidPCA in single-cell RNA and ATAC sequencing data."
doi: "10.1016/j.xhgg.2025.100538"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12720097/"
source_ids: {doc_id: "pmc:12720097", pmid: "41157948", pmcid: "12720097", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_gene_programs", "rna_clustering", "atac_clustering"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Find computational strategies for connecting noncoding AD GWAS risk variants to cell-type-specific scATAC peaks, genes, and regulatory programs, including validation and failure modes."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This paper introduces ResidPCA, a residual principal-component analysis method that regresses out cell-type-driven expression or chromatin-accessibility structure before applying PCA to identify cell states shared across cell types. It evaluates ResidPCA in simulations, light-stimulated mouse visual cortex scRNA-seq, and Alzheimer disease single-nucleus ATAC-seq and RNA-seq, showing that residualizing cell-type effects can reveal disease-relevant cellular states that standard PCA and NMF-based approaches miss.

## Hypothesis framed
Residualizing cell-type-driven variation before PCA will recover cross-cell-type disease-associated cell states from single-cell RNA-seq and ATAC-seq more accurately than conventional PCA, NMF-based methods, UMAP, or cell-type-specific analyses.

## Questions answered
- Does ResidPCA outperform standard PCA and NMF-based methods for recovering cell states that span multiple cell types in simulated single-cell data?
- Can ResidPCA recover experimentally induced light-stimulation transcriptional states in mouse visual cortex scRNA-seq better than NMF-based approaches?
- Do ResidPCA-derived chromatin accessibility states from Alzheimer disease snATAC-seq show stronger Alzheimer disease heritability enrichment than established cell-type annotations?

## Key findings
In simulations, ResidPCA achieved more than 4-fold higher accuracy than conventional PCA and more than 3-fold higher accuracy than NMF-based methods for detecting states expressed across multiple cell types. In light-stimulated mouse visual cortex scRNA-seq, ResidPCA captured stimulus-driven variability with more than 5-fold higher accuracy than NMF-based approaches, with strong performance in endothelial/smooth muscle and mural cell populations. In Alzheimer disease single-nucleus datasets, ResidPCA identified 44 chromatin accessibility states from snATAC-seq and 42 transcriptional states from snRNA-seq; 30 ATAC-derived states were significantly enriched for Alzheimer disease heritability, often exceeding enrichment for established cell types such as microglia.

## Methods used
Residual principal-component analysis after modeling and regressing out cell-type-driven expression or accessibility; benchmarking against standard PCA, iterative PCA, cNMF, NMF, scaled NMF, and UMAP; simulation studies varying cell-type heterogeneity and state abundance; R-squared evaluation of component accuracy using light exposure duration as a proxy for biological state in mouse visual cortex scRNA-seq; application to Alzheimer disease snATAC-seq and snRNA-seq; Alzheimer disease heritability enrichment testing for ResidPCA-derived accessibility states.

## Method and dataset
ResidPCA was applied to simulated single-cell matrices, light-stimulated mouse visual cortex scRNA-seq, Alzheimer disease cohort snATAC-seq, and Alzheimer disease cohort snRNA-seq. The method assumes that log-normalized single-cell expression or accessibility can be decomposed into cell-type-driven and state-driven components, and that cell-type labels or atlas projections are available for residualization. Dataset sizes and cohort sample counts were not provided in the summary.

## Limitations
ResidPCA depends on accurate cell-type annotation or atlas projection; incorrect cell-type labels can distort residualization and downstream state discovery. Its generative model uses simplified assumptions about decomposing log-normalized expression or accessibility into cell-type and state components, which may not capture all biological or technical variation. In the mouse visual cortex benchmark, light exposure duration was used as a proxy for true cell state and may not perfectly represent the transcriptional response or may be confounded with cell-type composition. Alzheimer disease interpretations were based on statistical heritability enrichment and inferred mechanistic links, without experimental validation of the identified states or regulatory effects.

## Evidence pattern
The paper defines ResidPCA as a method for cell-state discovery after removal of cell-type effects, then supports its claims through comparison-design benchmarking against PCA, iterative PCA, cNMF, NMF, scaled NMF, and UMAP. Evidence includes simulation accuracy under controlled cell-type heterogeneity and state-abundance settings, real-data validation using light exposure duration and within-cell-type R-squared in mouse visual cortex scRNA-seq, and Alzheimer disease heritability enrichment analysis of snATAC-seq-derived states. Boundary conditions are addressed through dependence on cell-type labels, simplified residualization assumptions, and the limitation that AD mechanistic conclusions are statistical rather than experimentally validated.

## Extends or contradicts
This paper extends standard PCA and NMF-based single-cell state discovery approaches by explicitly modeling and removing cell-type-driven variation before PCA. It does not directly perform AD GWAS variant-to-peak mapping, fine-mapping, variant-to-gene linking, co-accessibility analysis, eQTL integration, chromatin-contact integration, or experimental validation of noncoding variant effects.

## Boundary conditions
Works when: Works when single-cell RNA-seq or ATAC-seq data contain strong cell-type-driven variation that may obscure subtler state-driven variation, and when reasonably accurate cell-type annotations or atlas projections are available. It is designed for states shared across multiple cell types, rare states, or states confounded by cell-type composition, as tested in simulations, stimulated mouse visual cortex scRNA-seq, and Alzheimer disease snATAC-seq/snRNA-seq.
Fails when: Performance may degrade when cell-type annotations are inaccurate, missing, or too coarse for effective residualization. It may fail to isolate states when the assumed additive decomposition of log-normalized measurements into cell-type and state components is violated, when technical variation is not captured by the residualization model, or when the biological state proxy used for validation is itself confounded with cell-type composition. It does not by itself identify causal GWAS variants, link variants to target genes, or experimentally validate regulatory mechanisms.
