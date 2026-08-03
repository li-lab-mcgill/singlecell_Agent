---
paper_id: building_gene_regulatory_networks_2019
title: "Building gene regulatory networks from scATAC-seq and scRNA-seq using Linked Self Organizing Maps."
doi: "10.1371/journal.pcbi.1006555"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC6855564/"
source_ids: {doc_id: "pmc:6855564", pmid: "31682608", pmcid: "6855564", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "atac_peak_to_gene", "multi_grn_inference"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Map method classes for TF activity and regulatory network inference from single-cell multiome data and identify their assumptions/failure modes."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This paper presents SOMatic, a linked self-organizing map approach that builds separate SOMs for scATAC-seq chromatin accessibility regions and scRNA-seq genes, then links accessibility and expression metaclusters to infer draft regulatory networks. It matters for single-cell multiomic regulatory analysis because it was designed for sparse, noisy scATAC-seq data and for differentiation settings where pseudotime methods or methods requiring strongly separated cell types may be unsuitable.

## Hypothesis framed
Linked self-organizing maps can associate sparse scATAC-seq accessibility patterns with scRNA-seq expression patterns and recover biologically meaningful regulatory modules and draft gene regulatory networks during mouse pre-B cell differentiation.

## Questions answered
- Can linked SOMs connect scATAC-seq regions with nearby scRNA-seq genes showing coordinated single-cell behavior in a mouse pre-B cell differentiation time course?
- Do linked chromatin-expression metaclusters show stronger transcription-factor motif enrichment than random groupings or analyses based only on chromatin or expression changes?
- Does SOMatic provide more biologically interpretable region clustering than cisTopic for this scATAC-seq differentiation dataset?

## Key findings
SOMatic identified linked regulatory modules containing genomic regions with similar accessibility patterns and nearby genes with similar expression patterns in an inducible Ikaros overexpression mouse pre-B cell differentiation system. Linked metaclusters showed stronger motif enrichment than random grouping or analyses based only on chromatin or expression changes, recovered known Ikaros-related regulatory biology involving Igll1, Vpreb2, and Nr3c1, and predicted additional candidate Ikaros targets. In comparison with cisTopic, cisTopic separated cells by time point but produced fewer and broader region clusters and did not recover biologically relevant GO terms at the same locus-level resolution reported for SOMatic.

## Methods used
Separate self-organizing maps were trained for scATAC-seq chromatin accessibility regions and scRNA-seq gene-expression profiles. A linking function associated SOM metaclusters containing genomic regions and nearby genes with coordinated single-cell behavior. Linked metaclusters were evaluated using gene ontology enrichment, transcription-factor motif enrichment, differential chromatin accessibility, differential gene expression, and draft regulatory network construction. scATAC-seq clustering was compared with cisTopic using cell separation, region clustering, silhouette coefficients, biological interpretability, and locus-level resolution.

## Method and dataset
Method: SOMatic linked self-organizing maps for scATAC-seq and scRNA-seq integration. Data: matched mouse pre-B cell differentiation time-course data from a controlled Ikaros overexpression model, with two main time points described in the summary; cell and feature counts are not reported in the summary. Experimental design: chromatin and expression SOMs were generated separately and then linked to connect regulatory regions with nearby genes. Assumptions: regulatory regions and target genes show coordinated single-cell profiles, linked regions are near their target genes, motif enrichment in accessible regions is informative for candidate transcription-factor regulation, and SOM parameters/preprocessing preserve biologically meaningful metaclusters.

## Limitations
The demonstration was primarily limited to one mouse pre-B cell differentiation system with two main time points. Regulatory links are computational predictions based on co-patterning, genomic proximity, and motif enrichment and require experimental validation. Nearby peak-to-gene linking may miss long-range enhancer-promoter interactions or context-specific chromatin contacts. Performance may depend on dataset size, sparsity, preprocessing choices, and SOM parameter settings. The study did not provide systematic comparisons against SCENIC+, FigR, chromVAR, CellOracle, other TF activity or GRN inference methods, same-cell multiome benchmarks, quantitative TF activity accuracy metrics, or gold-standard regulatory edge validation beyond recovered known biology and candidate predictions.

## Evidence pattern
Entity definition: defines SOMatic as linked chromatin and gene-expression SOMs. Comparison design: compares scATAC-seq clustering and interpretability with cisTopic. Validation: uses recovery of known Ikaros-associated biology, GO enrichment, TF motif enrichment, and examples involving Igll1, Vpreb2, and Nr3c1. Boundary conditions: evaluates the method on a mouse pre-B cell Ikaros overexpression differentiation time course with sparse scATAC-seq and matched scRNA-seq. Analysis used: SOM metaclustering, linking by coordinated profiles and genomic proximity, motif enrichment, differential accessibility, differential expression, GO enrichment, silhouette coefficients, and draft GRN construction.

## Extends or contradicts
This paper extends prior single-cell regulatory analysis approaches that depend on pseudotime structure or highly distinct cell types by proposing linked SOMs for integrating noisy scATAC-seq with scRNA-seq in a subtler differentiation setting. It compared against cisTopic and reported that cisTopic separated cells by time point but produced broader, less biologically interpretable region clusters for this dataset.

## Boundary conditions
Works when: Works when matched or comparable scATAC-seq and scRNA-seq profiles are available for a biological process in which chromatin accessibility and nearby gene expression are expected to co-vary across cells or time points; when the goal is module-level regulatory hypothesis generation rather than experimentally validated enhancer-target assignment; and when nearby genomic association is an acceptable approximation for peak-to-gene linking.
Fails when: May fail or give incomplete networks when key regulatory interactions are long-range, trans-acting, or not captured by nearest-gene proximity; when chromatin accessibility and gene expression are temporally uncoupled; when scATAC-seq sparsity or small sample size prevents stable SOM metaclusters; when SOM parameters or preprocessing choices distort cluster structure; or when the task requires quantitative TF activity inference accuracy or experimentally validated regulatory edges.
