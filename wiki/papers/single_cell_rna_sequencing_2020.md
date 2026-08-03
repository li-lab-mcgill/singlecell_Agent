---
paper_id: single_cell_rna_sequencing_2020
title: "Single cell RNA sequencing of human microglia uncovers a subset associated with Alzheimer's disease."
doi: "10.1038/s41467-020-19737-2"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC7704703/"
source_ids: {doc_id: "pmc:7704703", pmid: "33257666", pmcid: "7704703", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_clustering", "rna_cell_type_annotation", "rna_differential_abundance"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["Learn which brain cell populations and disease-associated cellular states are reproducibly implicated in human Alzheimer's disease single-cell/nucleus transcriptomics, and how those states are biologically defined and validated."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study used single-cell RNA sequencing of purified live human cortical microglia from autopsy and neurosurgical samples to define microglial population structure. It identified 9 transcriptionally distinct microglial clusters and prioritized cluster 7 as an Alzheimer's disease-associated microglial subset reduced in AD tissue, with support from histology and independent single-nucleus data.

## Hypothesis framed
Live human cortical microglia contain transcriptionally distinct subpopulations, and some of these subpopulations are enriched for Alzheimer's disease-related gene signatures and altered in frequency in Alzheimer's disease tissue.

## Questions answered
- What transcriptionally distinct microglial subpopulations can be identified from purified live human cerebral cortex microglia?
- Are specific human microglial clusters enriched for neurodegenerative disease-related genes or Alzheimer's disease-associated RNA signatures?
- Is the Alzheimer's disease-associated cluster 7 microglial subset reduced in AD tissue and reproducible using histology and independent single-nucleus RNA-seq data?

## Key findings
The study identified 9 human cortical microglial clusters from approximately 16,000 high-quality single-cell transcriptomes across 17 donors. The clusters included homeostatic, proliferative, interferon-response, and antigen-presentation-associated microglial states, and several were enriched for neurodegenerative disease-related genes. Cluster 7 was enriched for genes depleted in Alzheimer's disease cortex; cluster 7 microglia were reduced in frequency in AD tissue by histological analysis, and this reduction was supported in an independent single-nucleus RNA-seq dataset.

## Methods used
Live brain myeloid cells were purified from human cerebral cortex samples obtained at autopsy and during neurosurgical procedures, followed by single-cell RNA-seq. The authors performed iterative PCA-Louvain clustering in Seurat, regressed out batch effects and total UMI counts, assessed cluster robustness using repeated random forest classification, merged unstable clusters, identified cluster marker genes and disease-gene enrichments, and validated selected subpopulations using immunohistochemistry, automated image analysis, and independent single-nucleus RNA-seq data.

## Method and dataset
Single-cell RNA-seq was applied to purified live human cortical microglia from 17 donors, yielding approximately 16,000 high-quality microglial transcriptomes. The experimental design combined autopsy and neurosurgical human cortex samples, clustered microglia after regression of batch effects and total UMI counts, and compared disease-associated signatures and microglial subset frequencies in Alzheimer's disease tissue. The clustering and abundance analyses assume that purified live microglia recovered from tissue preserve biologically meaningful transcriptional states and that regression of batch and UMI effects sufficiently controls major technical variation.

## Limitations
The study is observational and cannot determine whether the reduction of cluster 7 microglia causes, compensates for, or follows Alzheimer's disease pathology. Samples came from both autopsy and neurosurgical sources, which may differ in age, disease status, postmortem interval, tissue handling, and clinical context. Live-cell microglial purification may bias recovery toward certain microglial states and miss fragile or highly reactive cells. The donor number was modest, limiting power for inter-individual variability and clinical covariates. Histological validation was performed only for selected subpopulations, and the functional roles of the clusters were not experimentally tested.

## Evidence pattern
Entity definition: microglial states were defined as 9 transcriptional clusters from purified live human cortical microglia. Comparison design: clusters and disease-related gene enrichments were compared across microglial subsets, and cluster 7 frequency was compared between Alzheimer's disease and non-AD tissue. Statistical unit: individual microglial cells for clustering and gene signatures, with donor-derived tissue samples supporting disease comparisons. Metric: cluster membership, marker-gene enrichment, disease-gene/RNA-signature enrichment, and histological frequency of cluster-marker-positive microglia. Covariates/controls: batch effects and total UMI counts were regressed out during clustering. Validation: four microglial subpopulations were confirmed histologically; cluster 7 reduction in AD was supported by histology and an independent single-nucleus RNA-seq dataset. Boundary conditions: findings apply to purified live human cortical microglia rather than unbiased whole-brain multi-cell-type profiles.

## Extends or contradicts
This paper extends prior microglial heterogeneity and neurodegeneration studies by providing a human live-microglia single-cell atlas and showing that Alzheimer's disease is associated with reduction of a specific microglial subset, not only with emergence of activated microglial states. No direct contradiction to a listed existing wiki paper is specified.

## Boundary conditions
Works when: Applies to human cerebral cortex datasets enriched or purified for live microglia, with thousands of microglial transcriptomes, enough donors to assess cluster recurrence, and analyses that can control batch and sequencing-depth effects. The cluster 7 AD association is supported when microglial subsets are measured in cortical AD tissue and validated with orthogonal histology or independent single-nucleus RNA-seq.
Fails when: Does not provide evidence for non-microglial brain populations such as neurons, astrocytes, oligodendrocytes, OPCs, endothelial cells, or whole-cortex multi-cell-type disease maps. Findings may fail to generalize to datasets generated without live microglia purification, to brain regions outside cerebral cortex, to conditions with strong dissociation or postmortem biases, or to highly fragile/reactive microglial states not recovered by live-cell sorting.
