---
paper_id: aggregatebiovar_2021
title: "Differential gene expression analysis for multi-subject single-cell RNA-sequencing studies with aggregateBioVar."
doi: "10.1093/bioinformatics/btab337"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC8504643/"
source_ids: {doc_id: "pmc:8504643", pmid: "33970215", pmcid: "8504643", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_differential_expression"]
retrieval_goals: ["broad_background"]
retrieval_intents: ["What statistical guidance establishes that donors/samples, not cells, are the valid replication unit for inference (to avoid pseudoreplication) in single-cell RNA/ATAC studies?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
The paper formalizes a hierarchical negative-binomial model for multi-subject scRNA-seq that separates between-subject and between-cell variation, demonstrates via simulations and real human and porcine datasets that naïve cell-level DE testing inflates false discovery rates (FDR), and shows that pseudobulk aggregation (per cell type per subject) followed by bulk-RNA DE tools restores FDR control. The authors provide aggregateBioVar, a Bioconductor package, to implement the recommended pseudobulk workflow.

## Hypothesis framed
In multi-subject scRNA-seq studies, modeling subject-level biological variation (i.e., using subjects as the replication unit via pseudobulk aggregation) yields valid differential expression inference and controls FDR better than naïve cell-level tests that treat cells as independent replicates.

## Questions answered
- Does ignoring between-subject variation (treating cells as independent replicates) inflate false discovery rates in multi-subject scRNA-seq differential expression testing?
- Can pseudobulk aggregation (counts aggregated per cell type per subject) combined with bulk-RNA DE tools restore FDR control while retaining power in multi-subject scRNA-seq?

## Key findings
Simulations and analyses of real datasets (human skin, trachea, lung and a porcine cystic fibrosis model, GSE150211) showed that naïve cell-level differential expression tests that ignore subject-level variation substantially inflate FDR; aggregating counts by cell type within each subject (pseudobulk) and applying bulk-RNA-seq DE methods provides substantially better FDR control while maintaining comparable power. The findings held across transcriptome-wide simulations varying numbers of DE genes and signal-to-noise ratios and across technologies represented in the tested datasets.

## Methods used
Extended hierarchical negative-binomial (NB) count model adding a cell-level variation stage; parameter estimation procedures for the hierarchical NB; transcriptome-wide simulations varying number of DE genes and signal-to-noise ratios; comparison of DE methods (naïve cell-level tests vs pseudobulk + bulk-RNA tools); application to real multi-subject scRNA-seq datasets (human skin, trachea, lung; porcine cystic fibrosis model). Implementation provided as the aggregateBioVar Bioconductor package.

## Method and dataset
Method: hierarchical NB model for scRNA-seq counts and pseudobulk aggregation by cell type per subject, followed by bulk-RNA differential expression tools. Data: multi-subject single-cell RNA-seq datasets including human skin, trachea, lung and porcine cystic fibrosis data (GEO GSE150211); transcriptome-wide simulations spanning variable numbers of DE genes and signal-to-noise ratios. Experimental design: multi-subject, multi-cell-type scRNA-seq with subjects as biological replicates. Assumptions: counts follow a hierarchical NB process (between-subject and within-subject/cell variation), correct identification/aggregation of cells into cell-type/state groups, independence of subjects.

## Limitations
Relies on hierarchical NB assumptions; requires correct cell type/state labeling for aggregation—misclassification or heterogeneous states within an aggregation group can bias results; aggregation sacrifices some single-cell granularity and can mask within-subject heterogeneity; benchmarking limited to the presented simulations and selected datasets and may not generalize to all technologies, normalization choices, or complex designs (e.g., nested, longitudinal, severely unbalanced designs); no explicit validation for scATAC-seq.

## Evidence pattern
entity_definition, comparison_design, statistical_unit, validation, effect_metric, boundary_conditions

## Extends or contradicts
Extends prior informal proposals of pseudobulk aggregation by providing a formal hierarchical NB justification and empirical evidence that pseudobulk restores valid subject-level inference; does not support naive cell-level independent-replicate approaches and demonstrates their shortcomings.

## Boundary conditions
Works when: Works when: experiments have multiple biological subjects (subjects can serve as independent replicates) and cells can be reliably aggregated by cell type/state per subject; counts are reasonably modeled by a hierarchical negative-binomial (between-subject plus within-subject/cell variation); there is at least one subject per experimental condition and sufficient cells per subject–cell-type group to produce stable aggregated counts; applicable across the tested scRNA-seq technologies represented in the real datasets.
Fails when: Fails or is unvalidated when: NB hierarchical assumptions are violated (e.g., strong zero inflation or non-NB count behavior), cell types/states are misclassified or highly heterogeneous within aggregation groups, within-subject cell-level heterogeneity is the primary signal of interest (aggregation will mask it), experimental designs are complex (nested or longitudinal sampling) and were not evaluated here, or for data modalities not tested (e.g., single-cell ATAC-seq) where the model/assumptions may not hold.
