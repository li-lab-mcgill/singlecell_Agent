---
paper_id: single_cell_rna_alzheimers_2023
title: "Single-cell RNA sequencing analysis of human Alzheimer's disease brain samples reveals neuronal and glial specific cells differential expression."
doi: "10.1371/journal.pone.0277630"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9955959/"
source_ids: {doc_id: "pmc:9955959", pmid: "36827281", pmcid: "9955959", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_clustering", "rna_cell_type_annotation", "rna_differential_expression"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Identify what statistical unit of inference credible studies use for disease-associated cell-type-specific differential expression/accessibility in single-cell or single-nucleus datasets with donors, and what failure modes arise if cells are treated as independent."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study used 10x Genomics single-nucleus RNA-seq to profile more than 25,000 nuclei from postmortem brain samples from 2 early-stage Alzheimer’s disease cases and 2 age- and gender-matched controls. It clustered and annotated neuronal, glial, immune, and vascular populations and reported cell-type-specific Alzheimer’s-associated expression changes, with astrocytes and microglia showing the strongest transcriptomic effects. Its disease differential-expression evidence is exploratory because donor replication was extremely limited and donor-level covariates such as APOE genotype, CERAD score, and Thal amyloid phase were not measured.

## Hypothesis framed
Early-stage Alzheimer’s disease is associated with cell-type-specific transcriptional changes in human postmortem brain tissue, with distinct neuronal, glial, immune, and vascular cell populations showing different disease-associated gene-expression programs.

## Questions answered
- Which neuronal, glial, immune, and vascular cell populations can be resolved from single-nucleus RNA-seq of early-stage Alzheimer’s disease and matched control brain samples?
- Which cell types show the strongest Alzheimer’s-associated differential gene expression in this small postmortem cohort?
- Are microglial cell proportions reported as increased in Alzheimer’s disease samples relative to controls in this dataset?

## Key findings
The study identified transcriptionally distinct excitatory neurons, inhibitory neurons, astrocytes, microglia, oligodendrocyte-lineage or macroglial cells, endothelial cells, and pericytes. Astrocytes and microglia were reported to have the greatest Alzheimer’s-associated transcriptomic changes. The authors reported 3,693 differentially expressed genes across cell-type comparisons and described gene upregulation as a general feature of Alzheimer’s-associated changes. Microglia were reported as consistently increased in Alzheimer’s samples compared with controls, with a highly significant Fisher exact test result. Reported affected pathways included proteoglycan, HGF, IGF, VEGF, PAR1, ESR1, HIF-1, NRF1, and SOX2-related signaling or regulatory networks, particularly in astroglial populations.

## Methods used
Postmortem human brain nuclei were profiled with 10x Genomics Chromium single-nucleus RNA-seq, sequenced on Illumina NovaSeq 6000, and aligned to the human GRCh38 genome using Cell Ranger. The analysis used unsupervised clustering, marker-gene-based cell type annotation, cell-type-specific differential expression analysis, pathway or regulatory-network interpretation, and Fisher exact testing for reported cell-population differences.

## Method and dataset
Single-nucleus RNA-seq was applied to more than 25,000 nuclei from 4 human postmortem brain donors: 2 Alzheimer’s disease cases at Braak stage I and II and 2 age- and gender-matched controls, all male. The abstract and methods emphasize anterior hippocampal cortex or hippocampal samples, while parts of the results are described as frontal cortex-focused. The disease comparison appears to assume that nuclei sampled from these donors can support cell-type-specific disease-associated differential expression, but the summary does not indicate donor-level pseudobulk aggregation, mixed-effects modeling, or another approach using donor as the statistical unit of inference.

## Limitations
The cohort included only 2 Alzheimer’s disease cases and 2 controls, all male, making donor-to-donor variability a major concern. Alzheimer’s cases were Braak stage I and II, so findings may not generalize to later-stage or clinically advanced Alzheimer’s disease. APOE genotype, CERAD neuritic plaque score, and Thal amyloid phase were not measured. The manuscript contains an inconsistency about brain region, referring to hippocampal or anterior hippocampal cortex samples in some sections and frontal cortex-focused analyses in the results. The percentage of reads passing filter was relatively low. The study appears exploratory and lacks independent validation, protein-level confirmation, functional experiments, and clear donor-level statistical modeling.

## Evidence pattern
Entity definition: single nuclei grouped into marker-defined neuronal, glial, immune, and vascular cell types. Comparison design: Alzheimer’s disease versus matched control postmortem brain samples, with 2 donors per group. Statistical unit: the summary does not report clear donor-level pseudobulk or mixed-effects inference; some reported significance, including cell-population testing by Fisher exact test, may reflect cell-level or nucleus-level counts despite limited donor replication. Metrics: differentially expressed genes, cell-population differences, pathway or regulatory-network enrichment. Covariates: age and gender matching were used, but APOE genotype, CERAD score, Thal amyloid phase, and consistent brain-region handling were not available or unclear. Validation: no independent cohort, protein-level validation, or functional validation reported. Boundary condition: evidence is most appropriate for exploratory cell-type discovery and hypothesis generation, not definitive disease differential-expression inference.

## Extends or contradicts
Extends prior bulk Alzheimer’s disease transcriptomic observations by assigning disease-associated transcriptional changes to specific neuronal, glial, immune, and vascular cell populations. It does not directly extend or contradict any listed existing wiki paper.

## Boundary conditions
Works when: Applies as an exploratory single-nucleus RNA-seq analysis of human postmortem early-stage Alzheimer’s disease brain tissue when the goal is to identify broad cell classes, nominate disease-associated cell types, and generate candidate cell-type-specific expression programs from approximately 25,000 nuclei. The findings are most interpretable for male donors with early Braak stage I/II Alzheimer’s disease under the sampled brain-region conditions described in the study.
Fails when: Does not provide robust donor-level evidence for disease-associated differential expression when biological replication is required, because there are only 2 Alzheimer’s disease donors and 2 controls. Inference can fail through pseudoreplication if nuclei or cells are treated as independent observations rather than modeling donor as the unit of inference. Interpretation is also limited when APOE genotype, CERAD score, Thal amyloid phase, sex diversity, consistent brain-region definition, batch effects, independent validation, or protein/functional confirmation are required.
