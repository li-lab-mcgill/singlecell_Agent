---
paper_id: cellular_communities_2024
title: "Cellular communities reveal trajectories of brain ageing and Alzheimer's disease."
doi: "10.1038/s41586-024-07871-6"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC11877878/"
source_ids: {doc_id: "pmc:11877878", pmid: "39198642", pmcid: "11877878", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_cell_type_annotation", "rna_gene_programs", "rna_trajectory"]
retrieval_goals: ["broad_background"]
retrieval_intents: ["Understand how prior human single-cell AD studies define disease-relevant cell types and states in prefrontal cortex, and what biological programs a credible analysis should recover."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study built a single-nucleus RNA-seq atlas of the aged human dorsolateral prefrontal cortex using 1.65 million nuclei from 437 ROSMAP participants and defined 95 cellular subpopulations. It associated glial and neuronal subpopulations with amyloid-beta burden, tau pathology and cognitive decline, then used causal modelling and the BEYOND framework to infer multicellular trajectories distinguishing AD dementia from alternative brain ageing.

## Hypothesis framed
Alzheimer's disease progression in the aged human prefrontal cortex is driven by coordinated changes in specific cellular communities, rather than isolated cell-state changes, and these communities define a trajectory distinct from non-AD brain ageing.

## Questions answered
- Which prefrontal cortex cell subpopulations are associated with amyloid-beta burden, tau pathology and cognitive decline in older humans?
- Do microglial or astrocytic subpopulations mediate inferred relationships between amyloid-beta, tau pathology and cognition?
- Can cross-sectional single-nucleus RNA-seq profiles from aged human cortex be organized into cellular-community trajectories that separate AD dementia from alternative brain ageing?

## Key findings
The study identified 95 cell subpopulations in aged human dorsolateral prefrontal cortex and found AD-related associations across glial and neuronal populations. Causal modelling prioritized two lipid-associated microglial subpopulations: one linked to amyloid-beta proteinopathy and another mediating the inferred effect of amyloid-beta on tau pathology. It also prioritized an astrocyte subpopulation mediating the inferred effect of tau pathology on cognitive decline. BEYOND identified two major ageing trajectories: an AD dementia trajectory with increasing amyloid-beta, increasing tau burden and accelerated cognitive decline, and an alternative brain-ageing trajectory with low stable amyloid-beta, limited tau pathology and variable cognitive decline.

## Methods used
Single-nucleus RNA-seq atlas construction, clustering and cell-subpopulation annotation, association testing between cellular subpopulations and AD-related traits, causal modelling of relationships among amyloid-beta, tau pathology, cell populations and cognition, and BEYOND pseudotemporal modelling of cellular environments and coordinated multicellular communities.

## Method and dataset
The study analyzed post-mortem dorsolateral prefrontal cortex single-nucleus RNA-seq from 437 older ROSMAP participants, totaling 1.65 million nuclei after quality control. The design combined cross-sectional end-of-life cellular profiles with donor-level longitudinal cognitive data and quantitative neuropathology. BEYOND inferred pseudotemporal trajectories of cellular environments under the assumption that inter-individual variation across post-mortem samples can approximate progressive ageing and disease dynamics.

## Limitations
The data are observational and post-mortem, so temporal and causal relationships inferred by causal modelling and pseudotime require experimental validation. Sampling was limited to dorsolateral prefrontal cortex and may miss region-specific AD processes. BEYOND trajectories were inferred from cross-sectional end-of-life samples rather than longitudinal single-cell sampling within individuals. ROSMAP participant characteristics may limit generalizability to more diverse populations. Functional roles of the prioritized lipid-associated microglial and astrocyte subpopulations remain to be mechanistically tested.

## Evidence pattern
Entity definition: 95 single-nucleus RNA-seq cell subpopulations in aged human prefrontal cortex. Comparison design: donor-level associations with amyloid-beta burden, tau pathology, cognitive decline and inferred ageing trajectories. Statistical unit: individual ROSMAP donors with nucleus-level expression profiles summarized into subpopulation and cellular-environment features. Metrics: AD-related neuropathology burden, cognitive decline measures, subpopulation associations and inferred mediation relationships. Covariates: AD-related traits and longitudinal clinical-pathological donor metadata were used in modelling. Validation and boundary conditions: conclusions are computationally inferred from post-mortem DLPFC snRNA-seq and require functional validation.

## Extends or contradicts
Extends prior human single-cell and single-nucleus AD studies that reported disease-associated neuronal, glial and vascular cell states by placing AD-relevant subpopulations into inferred temporal cellular-community trajectories and by distinguishing an AD dementia path from alternative brain ageing.

## Boundary conditions
Works when: Applies to large post-mortem human single-nucleus RNA-seq datasets from aged cortex with hundreds of donors, sufficient nuclei to resolve rare or fine-grained glial and neuronal subpopulations, and matched donor-level neuropathology and cognitive phenotypes such as amyloid-beta burden, tau pathology and cognitive decline.
Fails when: Does not directly establish causal mechanisms or true within-person temporal dynamics; may fail or be unreliable in small cohorts, datasets without donor-level pathology and cognition, non-prefrontal brain regions not sampled in the study, longitudinal interpretations from purely cross-sectional data, or populations that differ substantially from ROSMAP enrollment characteristics.
