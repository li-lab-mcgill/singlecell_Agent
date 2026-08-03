---
paper_id: disease_associated_astrocytes_2020
title: "Disease-associated astrocytes in Alzheimer's disease and aging."
doi: "10.1038/s41593-020-0624-8"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9262034/"
source_ids: {doc_id: "pmc:9262034", pmid: "32341542", pmcid: "9262034", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_cell_type_annotation", "rna_differential_abundance", "rna_gene_programs"]
retrieval_goals: ["broad_background"]
retrieval_intents: ["Understand how prior human single-cell AD studies define disease-relevant cell types and states in prefrontal cortex, and what biological programs a credible analysis should recover."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study used single-nucleus RNA sequencing of hippocampal and prefrontal cortex samples from 5XFAD Alzheimer's disease model mice and wild-type mice across ages to identify non-neuronal transcriptional states associated with disease progression and aging. It defined a disease-associated astrocyte population that emerged early in the 5XFAD model, increased with disease progression, and had related states in aged wild-type mice and aging human brains.

## Hypothesis framed
Alzheimer's disease progression and brain aging are associated with a distinct astrocyte transcriptional state that can be detected by single-nucleus RNA sequencing and increases with disease-related or age-related pathology.

## Questions answered
- Does single-nucleus RNA sequencing identify a distinct astrocyte state associated with Alzheimer's disease-like pathology in 5XFAD mice?
- Does the abundance of disease-associated astrocytes change across early and advanced disease stages in the 5XFAD model?
- Are astrocyte states similar to 5XFAD disease-associated astrocytes detectable in aged wild-type mice and aging human brains?

## Key findings
The paper concluded that a distinct disease-associated astrocyte population is present in the 5XFAD Alzheimer's disease mouse model, appears at early disease stages, and increases in abundance with disease progression. Similar astrocyte states were also observed in aged wild-type mice and aging human brains, linking the state to both Alzheimer's disease-like pathology and aging-related factors.

## Methods used
Single-nucleus RNA sequencing of mouse hippocampus and prefrontal cortex; comparison across genotype, age, sex, and brain region; clustering and transcriptional profiling of non-neuronal nuclei; differential abundance assessment of astrocyte states across disease stage and aging; immunohistochemistry validation in 7-month-old mice; comparative analysis with aging human brain data.

## Method and dataset
The study analyzed single-nucleus RNA-seq data from hippocampal and prefrontal cortex samples of 5XFAD and wild-type mice across multiple ages, including early and advanced disease stages, with additional comparison to aged wild-type mice and aging human brains. The summary does not report nucleus counts, donor counts, or exact sample sizes. The analysis assumes that nuclear RNA profiles can resolve astrocyte disease states and that transcriptionally similar astrocyte clusters across mouse disease, mouse aging, and human aging represent related biological states.

## Limitations
The summary does not provide detailed statistical results, effect sizes, marker genes, donor-level modeling, or functional validation of the astrocyte state. The study relies heavily on the 5XFAD mouse model, which models amyloid pathology but does not reproduce all features of human Alzheimer's disease. Human evidence is comparative and observational, so whether disease-associated astrocytes drive pathology or respond to it remains unresolved.

## Evidence pattern
Entity definition through single-nucleus RNA-seq clustering of a disease-associated astrocyte population; comparison design across 5XFAD versus wild-type mice, ages, disease stages, sex, and brain regions; differential abundance pattern showing early emergence and increase with progression; validation by immunohistochemistry in 7-month-old mice; boundary-condition comparison showing related astrocyte states in aged wild-type mice and aging human brains.

## Extends or contradicts


## Boundary conditions
Works when: Applies to single-nucleus RNA-seq analyses of brain tissue where astrocyte nuclei are captured from Alzheimer's disease-like, aging, or control samples and where comparisons across genotype, age, disease stage, or brain region are available. The finding is most directly supported for 5XFAD mouse hippocampus and prefrontal cortex, with comparative support in aged wild-type mice and aging human brains.
Fails when: Does not establish causal roles for astrocytes in Alzheimer's disease progression, does not define primary human Alzheimer's disease prefrontal cortex case-control effects in detail, and may not generalize to Alzheimer's disease features absent from the 5XFAD amyloid-focused model. The summary does not support use for neuronal subtype definitions, oligodendrocyte disease programs, microglial disease programs, or donor-level human AD effect-size estimation.
