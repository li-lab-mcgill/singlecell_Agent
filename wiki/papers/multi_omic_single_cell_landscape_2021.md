---
paper_id: multi_omic_single_cell_landscape_2021
title: "A multi-omic single-cell landscape of human gynecologic malignancies."
doi: "10.1016/j.molcel.2021.10.013"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC8642316/"
source_ids: {doc_id: "pmc:8642316", pmid: "34739872", pmcid: "8642316", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "atac_peak_to_gene", "multi_grn_inference"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Determine computational method classes and failure modes for inferring transcription factor programs from single-cell ATAC or paired RNA+ATAC multiome data in cell-type-specific disease analyses."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This paper profiled fresh, treatment-naive human ovarian and endometrial tumors using matched scRNA-seq and scATAC-seq, analyzing 75,523 cells by RNA and 74,621 cells by ATAC from 11 patients. It links chromatin accessibility variation to gene expression in malignant cells and uses these links to identify cancer-associated regulatory elements and malignant-cell-specific transcription factor activities.

## Hypothesis framed
Matched single-cell transcriptome and chromatin accessibility profiling of gynecologic tumors can reveal malignant-cell-specific regulatory elements and transcription factor activities that explain tumor gene expression programs and intratumoral heterogeneity.

## Questions answered
- Can matched scRNA-seq and scATAC-seq from gynecologic tumors link malignant-cell chromatin accessibility variation to transcriptional output?
- Do malignant ovarian and endometrial tumor cells acquire cancer-specific non-coding regulatory elements associated with hallmark cancer pathways?
- Can transcription factor activity be inferred in a malignant-cell-type-specific manner from matched single-cell RNA and ATAC profiles?

## Key findings
Across 11 fresh gynecologic tumor specimens, the study found substantial cellular heterogeneity across and within tumors. Malignant cells showed cancer-specific chromatin accessibility programs, including previously unannotated regulatory elements associated with hallmark cancer pathways such as mTOR signaling. Within-patient malignant-cell variation in chromatin accessibility was linked to gene expression differences, and the analysis inferred malignant-cell-specific transcription factor activities.

## Methods used
Fresh surgical tumor specimens were dissociated into viable single-cell suspensions and profiled with matched scRNA-seq and scATAC-seq. The analysis used single-cell quality control, clustering, marker-based cell type annotation, clinical biomarkers including MUC16/CA125, WFDC2/HE4, and KIT/CD117, inferred copy-number alterations to distinguish malignant from non-malignant cells, integration of gene expression with chromatin accessibility, regulatory element identification, accessibility-to-expression linking, intratumoral heterogeneity analysis, and transcription factor activity inference.

## Method and dataset
Matched scRNA-seq and scATAC-seq were applied to fresh, treatment-naive ovarian cancers, endometrial cancers, and metastatic tumors involving the ovary from 11 patients undergoing surgery. After quality control, the dataset contained 75,523 scRNA-seq cells and 74,621 scATAC-seq cells. The design assumes that matched RNA and ATAC profiles from the same tumor specimens can be integrated to relate accessible regulatory elements to transcriptional output, even when RNA and ATAC are not necessarily measured in the exact same individual cells.

## Limitations
The cohort included only 11 patients and combined heterogeneous ovarian, endometrial, and metastatic tumor cases, limiting generalizability. The study was largely observational and computational, so inferred regulatory elements, enhancer-gene links, and transcription factor activities require functional validation. scRNA-seq and scATAC-seq were matched by tumor specimen but not necessarily from the same individual cells. Clinical outcome associations and treatment-response predictions were limited by cohort size and study design.

## Evidence pattern
The paper supports its claims through entity definition of malignant and non-malignant cell populations using clustering, marker genes, clinical biomarkers, and inferred copy-number alterations; statistical units consisting of single cells from 11 patient tumor specimens; paired specimen-level scRNA-seq and scATAC-seq analysis; integration of chromatin accessibility with gene expression; identification of candidate regulatory elements; and inference of transcription factor activity. Boundary conditions are explicitly shaped by the small heterogeneous cohort and lack of large-scale functional validation.

## Extends or contradicts
This paper extends single-cell cancer atlas studies by adding matched chromatin accessibility and transcriptome profiling in human gynecologic malignancies to connect non-coding regulatory elements with malignant-cell gene expression programs. It does not directly benchmark or contradict a prior computational method paper listed in the existing wiki.

## Boundary conditions
Works when: Applicable to fresh, viable tumor specimens processed immediately after surgical resection where matched scRNA-seq and scATAC-seq can be generated from the same tumor sample and where malignant populations can be separated from non-malignant cells using marker genes, clinical biomarkers, and inferred copy-number alterations.
Fails when: Findings may not generalize to larger or more uniform cohorts without validation because the study used 11 heterogeneous patients. Inferred enhancer-gene links and transcription factor activities may fail or be confounded when chromatin accessibility is sparse, when RNA and ATAC are not measured in the same cells, when tumor copy-number alterations affect accessibility or expression signals, when cell-type composition differs strongly across samples, or when motif redundancy prevents unambiguous transcription factor assignment.
