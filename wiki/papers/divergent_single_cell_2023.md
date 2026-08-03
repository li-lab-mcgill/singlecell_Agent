---
paper_id: divergent_single_cell_2023
title: "Divergent single cell transcriptome and epigenome alterations in ALS and FTD patients with C9orf72 mutation."
doi: "10.1038/s41467-023-41033-y"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC10504300/"
source_ids: {doc_id: "pmc:10504300", pmid: "37714849", pmcid: "10504300", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_differential_expression", "atac_differential_accessibility", "multiomic_integration"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Identify what statistical unit of inference credible studies use for disease-associated cell-type-specific differential expression/accessibility in single-cell or single-nucleus datasets with donors, and what failure modes arise if cells are treated as independent."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study profiled postmortem human motor cortex and dorsolateral prefrontal cortex from C9orf72 repeat expansion ALS, C9orf72 repeat expansion FTD, and control donors using snRNA-seq, snATAC-seq, FANS-sorted bulk RNA-seq, H3K27ac ChIP-seq, and automated Western blotting. It found that C9-ALS and C9-FTD have divergent cell-type-, brain-region-, and disease-specific molecular alterations, with widespread neuronal and astrocytic disruption in C9-ALS and more prominent glial transcriptional changes plus reduced high-quality neuronal nuclei in C9-FTD frontal cortex.

## Hypothesis framed
C9orf72 repeat expansion produces distinct transcriptomic and epigenomic alterations across ALS and FTD that depend on clinical syndrome, cortical region, and cell type.

## Questions answered
- Which cortical cell types show the strongest C9-ALS-associated gene expression and chromatin accessibility alterations?
- Do C9-ALS-associated transcriptomic changes correspond to concordant chromatin accessibility and H3K27ac histone acetylation changes?
- Are molecular effects of C9orf72 repeat expansion similar or divergent between C9-ALS and C9-FTD across motor and frontal cortex?

## Key findings
The snRNA-seq dataset included 17 donors, 105,120 high-quality nuclei, 49 fine-grained cell subpopulations, and 14 major neuronal and glial cell types used for statistical analysis. C9-ALS showed pervasive gene expression alterations, strongest in upper-layer excitatory neurons, deep-layer excitatory neurons, and astrocytes; many expression changes were supported by concordant snATAC-seq chromatin accessibility and H3K27ac ChIP-seq changes. Neuronal changes in C9-ALS indicated increased proteostasis, metabolism, and protein expression pathways with decreased neuronal functional programs, while astrocyte changes indicated activation, reactive remodeling, structural remodeling, and disease-associated astrocyte states. C9-FTD showed fewer high-quality neuronal nuclei in frontal cortex and prominent gene expression changes in glial populations, supporting divergent C9orf72-associated molecular pathology between ALS and FTD.

## Methods used
Single-nucleus RNA-seq of frozen postmortem dorsolateral prefrontal cortex and motor cortex; single-nucleus ATAC-seq; FANS-sorted bulk RNA-seq; H3K27ac ChIP-seq; automated Western blotting; fine-grained nucleus clustering into 49 subpopulations; grouping into 14 major neuronal and glial cell types; disease-versus-control comparisons for C9-ALS and C9-FTD across cell types and brain regions; integration of differential gene expression with chromatin accessibility, H3K27ac, and protein-level measurements.

## Method and dataset
The study analyzed postmortem dorsolateral prefrontal cortex and motor cortex from C9-ALS, C9-FTD, and neuropathologically normal control donors. The snRNA-seq component contained 17 donors and 105,120 high-quality nuclei, annotated into 49 subpopulations and grouped into 14 major cell types for disease-associated analyses. The design compared C9-ALS versus controls and C9-FTD versus controls within cell types and brain regions, and related RNA changes to snATAC-seq accessibility, H3K27ac ChIP-seq, FANS-sorted bulk RNA-seq, and protein measurements. The disease-association analysis assumes that donor-level disease groups and postmortem cortical regions are appropriate units for comparing C9orf72-associated molecular states, rather than interpreting isolated nuclei without donor and brain-region context.

## Limitations
The study used a relatively small number of postmortem donors, limiting statistical power and representation of clinical heterogeneity. Samples were collected at end-stage disease, so observed molecular changes may reflect late consequences rather than initiating mechanisms. C9-FTD samples produced substantially fewer high-quality nuclei than controls or C9-ALS samples, especially limiting interpretation of neuronal changes in frontal cortex. The study was restricted to selected cortical regions and may not capture disease biology in spinal cord or other relevant brain regions. As an observational postmortem analysis, it identifies disease-associated molecular alterations but does not establish causal mechanisms.

## Evidence pattern
The paper uses an entity-definition and comparison-design pattern: C9-ALS, C9-FTD, and control donors are compared across motor and frontal cortex, with nuclei annotated into fine-grained subpopulations and major cell types. The statistical-unit evidence is based on a multi-donor postmortem design with disease-associated analyses performed across donor-defined disease groups, cell types, and brain regions. Validation and triangulation come from concordance between snRNA-seq differential expression, snATAC-seq accessibility changes, H3K27ac ChIP-seq, FANS-sorted bulk RNA-seq, and automated Western blotting. Boundary conditions include small donor number, end-stage tissue, and reduced high-quality neuronal nuclei in C9-FTD frontal cortex.

## Extends or contradicts
This paper extends prior human neurodegeneration single-nucleus studies by jointly analyzing transcriptomic and epigenomic alterations in C9orf72 ALS and FTD across disease phenotype, cortical region, and cell type. It does not directly extend or contradict any listed wiki paper.

## Boundary conditions
Works when: The findings apply to postmortem human cortical tissue from donors with C9orf72 repeat expansion ALS, C9orf72 repeat expansion FTD, and neuropathologically normal controls; to frozen dorsolateral prefrontal cortex and motor cortex; and to analyses with donor-level disease groups, annotated neuronal and glial cell types, and sufficient high-quality nuclei for a given cell type and brain region.
Fails when: Interpretation is weakened for cell types or regions with few high-quality nuclei, particularly neuronal analyses in C9-FTD frontal cortex. The design does not determine early pathogenic events, causality, or molecular effects outside the sampled cortical regions. The summary does not report an explicit analysis of pseudoreplication or inflated significance from treating individual nuclei as independent observations.
