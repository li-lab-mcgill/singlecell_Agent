---
paper_id: from_single_cell_clusters_2026
title: "From Single-Cell Clusters to Causality: ITCH Engagement for CKD Uncovered by Integrative Analysis of MR and MAGMA."
doi: "10.1096/fj.202502366R"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12980694/"
source_ids: {doc_id: "pmc:12980694", pmid: "41817007", pmcid: "12980694", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_differential_expression", "rna_cell_type_annotation", "rna_differential_abundance"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Identify what statistical unit of inference credible studies use for disease-associated cell-type-specific differential expression/accessibility in single-cell or single-nucleus datasets with donors, and what failure modes arise if cells are treated as independent."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study integrated public human kidney scRNA-seq from five donors with CKD GWAS, Mendelian randomization, MAGMA gene-level association, network analysis, and computational drug-prioritization analyses to identify CKD susceptibility genes. It used donor-level pseudobulk aggregation within cell types rather than individual cells as independent observations for differential expression, and prioritized ITCH as a high-confidence CKD-associated candidate supported by transcriptomic dysregulation, genetic evidence, and immunohistochemistry in an experimental kidney injury model.

## Hypothesis framed
Donor-aware cell-type-specific pseudobulk differential expression integrated with CKD GWAS-based MR and MAGMA analyses can identify plausible CKD susceptibility genes, with ITCH representing a candidate involved in CKD pathobiology and potentially modifiable by drug-like compounds.

## Questions answered
- Can donor-level pseudobulk differential expression in a small human kidney scRNA-seq dataset be integrated with MR and MAGMA to prioritize CKD susceptibility genes?
- Which CKD-associated gene receives convergent support from kidney scRNA-seq dysregulation, genetic association, and causal-inference analyses?
- Does ITCH show increased expression in diseased kidney tissue in an experimental injury validation model?

## Key findings
The study analyzed 15,896 cells from five human kidney donors, including three CKD and two healthy-control samples, and annotated 12 renal, stromal, vascular, and immune cell populations. CKD kidneys showed compositional remodeling, including reduced tubular epithelial fractions and expanded stromal and immune compartments. Donor-aware pseudobulk differential expression within cell types showed broadly concordant directionality with exploratory cell-level results, and integration of pseudobulk DEGs with MR and MAGMA prioritized ITCH as the strongest high-confidence candidate. ITCH expression was particularly notable in distal convoluted tubule cells, and immunohistochemistry in an experimental kidney injury model supported ITCH upregulation in diseased kidneys. DSigDB enrichment, molecular docking, and 50-ns molecular dynamics simulations nominated hesperetin as a computationally prioritized compound for future ITCH-modulation testing.

## Methods used
Human kidney scRNA-seq quality control, normalization, clustering, cell-type annotation into 12 populations, exploratory cell-level differential expression, donor-level pseudobulk aggregation within cell types, edgeR quasi-likelihood differential expression modeling, cell-type composition comparison, integration with cis-eQTL instruments, two-sample Mendelian randomization using CKD-related GWAS summary statistics, pleiotropy-robust MR sensitivity analyses, MAGMA gene-level association testing, network analysis, immunohistochemistry in an experimental kidney injury model, DSigDB drug enrichment, molecular docking, and 50-ns molecular dynamics simulations.

## Method and dataset
The primary transcriptomic analysis used public human kidney scRNA-seq from five donors, with three CKD and two healthy-control samples and 15,896 cells retained after quality control. Cells were clustered and annotated into 12 kidney and immune cell types; for differential expression, counts were aggregated by donor within each cell type and modeled with edgeR quasi-likelihood methods, making the donor rather than the cell the statistical unit. The pseudobulk approach assumes that biological replication occurs at the donor level and is intended to reduce cell-level pseudoreplication in a small-donor disease-control design.

## Limitations
The human scRNA-seq dataset included only five donors, limiting power, covariate adjustment, and generalizability despite donor-aware pseudobulk modeling. MR and MAGMA provide genetic support but depend on instrument validity, pleiotropy assumptions, and the relevance of the GWAS and eQTL contexts, and therefore do not prove molecular mechanism. Immunohistochemistry validation was performed in an experimental kidney injury model rather than an independent human CKD cohort. Hesperetin was nominated only by computational enrichment, docking, and molecular dynamics simulation, with no experimental evidence that it binds or modulates ITCH or changes CKD progression.

## Evidence pattern
Entity definition: CKD versus healthy-control human kidney donors, with cell types defined by scRNA-seq clustering and annotation. Comparison design: disease-control comparison within each annotated cell type. Statistical unit: donor-level pseudobulk samples within cell type, not individual cells. Analysis used: edgeR quasi-likelihood differential expression on pseudobulk counts, followed by convergence with cis-eQTL-based two-sample MR and MAGMA gene-level association using CKD-related GWAS summary statistics. Validation: immunohistochemistry in an experimental kidney injury model for ITCH upregulation. Boundary condition: the study explicitly addresses pseudoreplication risk in small-donor scRNA-seq disease studies but does not quantify false-positive inflation from treating cells as independent.

## Extends or contradicts
This paper supports the existing methodological finding that, in multi-donor single-cell disease studies, the biological donor should be the unit of inference for cell-type-specific differential expression. It applies that donor-aware pseudobulk principle to CKD kidney scRNA-seq and downstream genetic prioritization, but it does not provide a formal benchmark against mixed models or contradict prior pseudobulk recommendations.

## Boundary conditions
Works when: Applies to case-control scRNA-seq studies with identifiable biological donors, annotated cell types, and enough cells per donor-cell-type stratum to form pseudobulk profiles. The approach is most appropriate when the research question is cell-type-specific disease-associated RNA differential expression and when donor-level replication, rather than cell count, defines inferential sample size.
Fails when: Treating individual cells as independent observations can produce pseudoreplication because cells from the same donor share biological and technical dependencies. The approach has limited power and limited ability to adjust for donor-level covariates when donor numbers are very small, as in this five-donor dataset. The evidence does not directly apply to single-cell chromatin accessibility, differential accessibility, Alzheimer's disease brain snRNA-seq, or settings requiring proof of ITCH mechanism or experimental validation of hesperetin activity.
