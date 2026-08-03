---
paper_id: single_nucleus_transcriptomics_2025
title: "Single-nucleus transcriptomics reveals a distinct microglial state and increased MSR1-mediated phagocytosis as common features across dementia subtypes."
doi: "10.1186/s13073-025-01519-4"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12359983/"
source_ids: {doc_id: "pmc:12359983", pmid: "40826098", pmcid: "12359983", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_differential_abundance", "rna_differential_expression", "rna_gene_programs"]
retrieval_goals: ["broad_background"]
retrieval_intents: ["Understand how prior human single-cell AD studies define disease-relevant cell types and states in prefrontal cortex, and what biological programs a credible analysis should recover."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study used single-nucleus RNA-seq of postmortem prefrontal cortex from controls and individuals with AD, DLB, or PDD to compare cell type-specific transcriptomic changes across dementia subtypes. It identified increased microglial proportions and a shared MSR1-positive microglial state linked to oligodendrocyte interaction and myelin phagocytosis, supported by RNAscope, immunohistochemistry, human tissue assays, mouse microglia, and cellular overexpression experiments.

## Hypothesis framed
AD, DLB, and PDD share cell type-specific transcriptomic programs in prefrontal cortex, including a microglia-oligodendrocyte interaction state in which microglial MSR1 promotes myelin-associated phagocytosis.

## Questions answered
- Are microglial proportions increased in prefrontal cortex across AD, DLB, and PDD compared with non-cognitive impairment controls?
- Do AD, DLB, and PDD share cell type-specific differentially expressed genes or pathways, particularly in microglia and oligodendrocytes?
- Is microglial MSR1 upregulation associated with myelin phagocytosis across dementia subtypes?

## Key findings
In 20 human prefrontal cortex samples, including 4 non-cognitive impairment controls, 4 AD, 6 DLB, and 6 PDD cases, microglial proportions were elevated in all dementia subtypes compared with controls. DLB and PDD clustered more closely with each other than with AD and shared more differentially expressed genes and pathways, especially in microglia. MSR1 was upregulated in microglia across AD, DLB, and PDD, HSPA1A was increased in oligodendrocytes, microglia and oligodendrocytes were spatially closer in PDD cortex than in control cortex, MSR1-positive microglia colocalized with MBP in PDD tissue, and MSR1 overexpression increased microglial phagocytosis of myelin.

## Methods used
Single-nucleus RNA sequencing of postmortem human prefrontal cortex; major brain cell type annotation; cell proportion analysis; cell type-specific differential gene expression; pathway analysis; inferred microglia-oligodendrocyte interaction analysis; RNAscope; immunohistochemistry; biochemical assays; analysis of human cortical tissue; primary microglia assays; LRRK2-G2019S Parkinson's disease mouse model; MSR1 overexpression and myelin treatment experiments in microglial cells.

## Method and dataset
The study analyzed snRNA-seq data from postmortem prefrontal cortex of 20 individuals: 4 non-cognitive impairment controls, 4 AD, 6 DLB, and 6 PDD. After quality control, tens of thousands of nuclei were assigned to excitatory neurons, inhibitory neurons, oligodendrocytes, oligodendrocyte precursor cells, astrocytes, microglia, endothelial cells, and ependymal cells, followed by diagnosis-level comparisons of cell abundance, cell type-specific gene expression, pathways, and inferred cell-cell interactions. The interpretation assumes that postmortem nuclear RNA profiles preserve disease-relevant cell states, that diagnostic groups are comparable despite small sample sizes, and that mouse and cellular assays can model aspects of human MSR1-mediated microglial myelin phagocytosis.

## Limitations
The human cohort was small, especially the AD and control groups. Samples were limited to postmortem prefrontal cortex, so findings may not generalize to other brain regions or earlier disease stages. Dementia cases may include mixed neuropathology, complicating subtype-specific interpretation. The cross-sectional postmortem design cannot determine temporal order or causality. Mouse and cellular validation models may not fully reproduce human dementia biology, and larger functional studies are needed.

## Evidence pattern
The paper used a comparison design across NCI, AD, DLB, and PDD; defined major brain cell entities by snRNA-seq clustering and annotation; measured differential cell abundance, cell type-specific differential expression, pathway enrichment, and inferred microglia-oligodendrocyte interactions; supported spatial and molecular claims with RNAscope, immunohistochemistry, biochemical assays, human tissue validation, mouse primary microglia, and MSR1 perturbation experiments; and bounded conclusions to postmortem prefrontal cortex and the available dementia subtypes.

## Extends or contradicts
This paper extends prior human single-cell dementia work by comparing AD, DLB, and PDD in the same prefrontal cortex snRNA-seq framework and by experimentally validating MSR1-positive microglial myelin phagocytosis as a shared dementia-associated program. No direct contradiction with an existing listed wiki paper is specified in the summary.

## Boundary conditions
Works when: Findings apply to postmortem human prefrontal cortex snRNA-seq data from clinically and pathologically defined AD, DLB, PDD, and non-cognitive impairment control groups, with enough nuclei to resolve major brain cell types and microglial/oligodendrocyte transcriptomes. The MSR1 phagocytosis evidence is strongest when supported by orthogonal spatial protein/RNA assays and functional microglial myelin uptake experiments.
Fails when: The findings may not hold in other brain regions, early or prodromal disease stages, cohorts with substantial unmodeled mixed pathology, or datasets too small to resolve microglial and oligodendrocyte states. The cross-sectional design cannot establish whether MSR1 upregulation precedes myelin pathology, and mouse or cultured microglial models may fail to capture the full human dementia microenvironment.
