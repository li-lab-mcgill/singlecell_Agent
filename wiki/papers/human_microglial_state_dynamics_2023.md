---
paper_id: human_microglial_state_dynamics_2023
title: "Human microglial state dynamics in Alzheimer's disease progression."
doi: "10.101/j.cell.2023.08.037"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC10644954/"
source_ids: {doc_id: "pmc:10644954", pmid: "37774678", pmcid: "10644954", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_cell_type_annotation", "rna_differential_expression", "multiomic_integration"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["Learn which brain cell populations and disease-associated cellular states are reproducibly implicated in human Alzheimer's disease single-cell/nucleus transcriptomics, and how those states are biologically defined and validated."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study profiled approximately 194,000 single-nucleus microglial transcriptomes and epigenomes from post-mortem human brain tissue across 443 ROSMAP participants spanning no, low, and high Alzheimer's disease pathology. It defined 12 human microglial transcriptional states, identified AD-stage- and state-specific gene-expression changes, integrated RNA, ATAC, motif, and regulatory-network analyses, and experimentally tested selected predicted regulators in human iPSC-derived microglia-like cells.

## Hypothesis framed
Human microglia occupy discrete transcriptional states during Alzheimer's disease progression, and these states are shaped by identifiable transcriptional and epigenomic regulatory programs that can explain AD-stage-specific gene-expression changes and AD-risk gene activity.

## Questions answered
- Which human microglial transcriptional states are detected across Alzheimer's disease pathological progression in post-mortem brain?
- Which microglial genes are differentially expressed across AD pathology stages, and are these changes state-specific or disease-stage-specific?
- Can transcriptomic and epigenomic integration nominate transcription factors and regulatory networks that drive homeostatic or inflammatory microglial state transitions?

## Key findings
The study identified 12 distinct human microglial transcriptional states, including homeostatic, neuronal-surveillance, ribosome-biogenesis, lipid-processing, phagocytic, stress-related, glycolytic, and inflammatory states. It found 1,542 AD-associated differentially expressed genes with both microglial-state-specific and AD-stage-specific alterations. Integrated snRNA-seq, snATAC-seq, motif, enhancer-gene, and regulatory-network analyses nominated upstream regulators and candidate drivers of microglial state transitions; ectopic expression of predicted homeostatic-state activators induced homeostatic features in iPSC-derived microglia-like cells, while inhibition of inflammatory activators blocked inflammatory progression. AD-risk genes localized to specific microglial states and showed differential expression or regulator changes during AD progression.

## Methods used
Single-nucleus RNA-seq, single-nucleus ATAC-seq, microglial transcriptional-state clustering and annotation using marker genes and pathway enrichment, empirical grouping of individuals into no, low, and high AD pathology using pathology and cognition measures, differential gene-expression analysis across AD pathology stages and microglial states, integration of transcriptomic and epigenomic data, motif analysis, enhancer-gene linking, gene-regulatory-network inference, transcription-factor state-transition inference, AD-risk gene mapping, and perturbation validation in human iPSC-derived microglia-like cells.

## Method and dataset
The study analyzed approximately 194,000 single-nucleus microglial transcriptomes and epigenomes from post-mortem human brain tissue from 443 ROSMAP participants with diverse Alzheimer's disease pathological and cognitive phenotypes. The experimental design compared microglia across empirically defined no, low, and high AD pathology groups and multiple brain regions, assuming that post-mortem single-nucleus RNA and ATAC profiles preserve biologically meaningful microglial state and regulatory information and that integrated chromatin accessibility, motif enrichment, and expression covariation can nominate candidate regulators and enhancer-gene links.

## Limitations
The study used post-mortem observational tissue, so causal temporal dynamics of microglial state transitions were inferred rather than directly observed. AD groups were based on empirical clustering of pathology and cognition rather than standard diagnostic criteria. Tissue quality, post-mortem interval, regional sampling, and donor heterogeneity may influence single-nucleus profiles. Single-nucleus assays can under-detect cytoplasmic transcripts and some activation programs. Regulatory networks and enhancer-gene links are computational predictions, and only selected regulators were experimentally validated in iPSC-derived microglia-like cells, which may not fully recapitulate adult human brain microglia. The study did not assess non-microglial brain cell types and does not by itself establish reproducibility across independent human AD single-cell cohorts.

## Evidence pattern
Entity definition: 12 microglial transcriptional states were annotated from snRNA-seq clusters using marker genes and pathway enrichment. Comparison design: microglia from 443 ROSMAP participants were compared across empirically defined no, low, and high AD pathology groups. Statistical unit: human subjects and single nuclei from post-mortem microglial populations. Effect metric: AD-associated differential expression comprising 1,542 genes, plus state-specific expression, chromatin accessibility, motif, enhancer-gene, and regulatory-network evidence. Controls/covariates: pathology and cognition measures were used to stratify disease progression; donor and tissue heterogeneity were considered as limitations. Validation: selected predicted regulators were perturbed in human iPSC-derived microglia-like cells, showing induction of homeostatic features or blockade of inflammatory progression. Boundary conditions: conclusions apply to human post-mortem microglia profiled by single-nucleus RNA and ATAC assays across AD pathological progression.

## Extends or contradicts
This paper extends prior human and mouse Alzheimer's disease microglial activation studies by resolving a large-scale human post-mortem microglial atlas with 12 transcriptional states, AD-stage-specific differential expression, and integrated epigenomic regulatory predictions. It also reports that human microglial disease signatures differ from mouse disease-associated microglia signatures, limiting direct cross-species generalization.

## Boundary conditions
Works when: Findings are most applicable to large human post-mortem brain cohorts with isolated or identifiable microglial nuclei, matched snRNA-seq and snATAC-seq or comparable multiomic data, sufficient donor-level AD pathology and cognition metadata, and enough nuclei to resolve rare microglial transcriptional states across disease stages.
Fails when: Findings should not be assumed to apply to excitatory neurons, inhibitory neurons, astrocytes, oligodendrocytes, OPCs, endothelial cells, peripheral myeloid cells, live-cell temporal dynamics, or mouse microglial disease states without validation. Regulatory predictions may fail when chromatin accessibility, motif activity, and expression covariation do not reflect causal regulation, and iPSC-derived microglia-like perturbation results may not transfer directly to adult human AD brain microglia in situ.
