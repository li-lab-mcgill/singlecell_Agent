---
paper_id: analysis_single_nuclear_chromatin_2024
title: "Analysis of single nuclear chromatin accessibility reveals unique myeloid populations in human pancreatic ductal adenocarcinoma."
doi: "10.1002/ctm2.1595"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC10905544/"
source_ids: {doc_id: "pmc:10905544", pmid: "38426634", pmcid: "10905544", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_clustering", "atac_cell_type_annotation", "multiomic_integration"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["Obtain marker definitions for DC subsets cDC1, cDC2, pDC in human PBMC by scRNA and scATAC"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
This study applies 10x single-nucleus ATAC-Seq (snATAC-Seq) to frozen human pancreatic tissue (4 PDAC, 4 benign) to resolve myeloid chromatin heterogeneity, identify eight distinct myeloid subpopulations with unique promoter accessibility and GO-enriched functions, and links a dendritic-cell promoter-accessibility signature to improved survival in TCGA-PAAD. Results were integrated with snMultiome RNA and validated by immunofluorescence, demonstrating snATAC-Seq can distinguish functional myeloid states in archived human PDAC tissue.

## Hypothesis framed
snATAC-Seq profiling of frozen human pancreatic tissue can resolve distinct myeloid subpopulations and their regulatory programs in PDAC, and promoter-accessibility-derived gene signatures (e.g., dendritic cells) will correlate with clinical outcomes in PDAC.

## Questions answered
- Can snATAC-Seq distinguish distinct myeloid subpopulations in frozen human PDAC tissue compared with benign pancreas?
- Are tumor-infiltrating myeloid cells characterized by higher transcription factor activity than benign pancreatic myeloid cells?
- Is a dendritic-cell-associated promoter accessibility signature associated with survival in TCGA-PAAD?

## Key findings
1) Identified eight distinct myeloid subpopulations by snATAC-Seq in human pancreatic tissue. 2) Myeloid cells from PDAC samples showed higher inferred transcription factor activity than benign pancreatic myeloid cells. 3) GO enrichment linked specific subclusters to functions (example: recruited monocytes enriched for interleukin-1β signaling; a dendritic cell cluster enriched for intracellular protein transport). 4) A dendritic cell promoter-accessibility gene signature was associated with improved survival in TCGA-PAAD (hazard ratio = 0.63, p = 0.03). 5) Cell-type annotations were supported by integration with an additional snMultiome RNA sample and by immunofluorescence validation.

## Methods used
Single-nucleus ATAC-Seq (10x Chromium) on frozen pancreatic tissue nuclei; Signac for preprocessing, dimensionality reduction and clustering; differential accessibility analysis; annotation of promoter-associated peaks to genes; Gene Ontology enrichment; transcription factor activity inference from chromatin accessibility/motif analysis; integration with snMultiome RNA; immunofluorescence validation; survival association testing using TCGA-PAAD bulk data.

## Method and dataset
Applied snATAC-Seq (10x Chromium) to nuclei from n=8 frozen surgical specimens (4 treatment-naïve PDAC, 4 benign pancreas), with FACS purification of nuclei. Promoter peaks were annotated to genes for GO and signature derivation. Integration used one additional snMultiome RNA sample for cross-modal annotation and immunofluorescence for spatial/protein validation. Survival associations used bulk TCGA-PAAD expression data. Assumptions: promoter chromatin accessibility reflects regulatory activity and cell identity; bulk TCGA signals can proxy cell-type–relevant signatures.

## Limitations
Small cohort (n=8 patients) limits generalizability and statistical power; samples restricted to treatment-naïve resections from the pancreatic head (possible anatomical/treatment bias); snATAC-Seq infers regulatory state but does not directly measure transcript or protein levels—functional inferences require further validation; survival associations derived from bulk TCGA data may be confounded by mixed cell-type signals; potential batch effects and lack of spatial resolution beyond validation IF.

## Evidence pattern
entity_definition, comparison_design, statistical_unit, validation, boundary_conditions

## Extends or contradicts
Extends prior single-cell chromatin and multiomic integration approaches by applying snATAC-Seq to frozen human PDAC tissue to define myeloid subclusters and derive promoter-accessibility signatures linked to outcome; does not directly contradict prior reports but complements single-cell RNA-based immune atlases by providing chromatin-level resolution.

## Boundary conditions
Works when: Works when: input is frozen human pancreatic tissue (treatment-naïve resections) with sufficient myeloid cell infiltration; nuclei can be isolated and FACS-purified for 10x Chromium snATAC-Seq; analysis includes promoter-associated peak annotation and integration with RNA (snMultiome) or orthogonal validation (immunofluorescence); cohort-level survival testing is performed using TCGA-PAAD.
Fails when: Fails when: applied to PBMC-only datasets without tissue-specific context (results are not PBMC DC marker definitions); sample size is too small or myeloid representation is low (<few hundred myeloid nuclei) to robustly define subclusters; applied to treated or non-head pancreatic samples without accounting for batch/clinical differences; relying solely on bulk survival datasets for cell-type–specific conclusions without single-cell deconvolution; when direct transcript/protein measurements are required to confirm inferred regulatory activity.
