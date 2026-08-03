---
paper_id: integrated_singlecell_2023
title: "Integrated single-cell analysis-based classification of vascular mononuclear phagocytes in mouse and human atherosclerosis."
doi: "10.1093/cvr/cvac161"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC10325698/"
source_ids: {doc_id: "pmc:10325698", pmid: "36190844", pmcid: "10325698", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_batch_correction", "rna_cell_type_annotation", "multi_cell_type_annotation"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["Obtain marker definitions for DC subsets cDC1, cDC2, pDC in human PBMC by scRNA and scATAC"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
This study integrates 12 mouse and 3 human scRNA-seq datasets (22,852 mouse cells; 11 human patients) using Seurat v3 to refine nomenclature of vascular mononuclear phagocytes in atherosclerosis and to test cross-species conservation. It defines discrete macrophage and dendritic cell transcriptional states in mouse aorta and maps homologous states to human coronary and carotid lesions, providing marker gene signatures for these states.

## Hypothesis framed
Discrete mononuclear phagocyte transcriptional states identified in mouse atherosclerotic vessels are conserved in human atherosclerotic lesions and can be robustly delineated by integrated single-cell transcriptomics to refine nomenclature.

## Questions answered
- Which macrophage and dendritic cell subpopulations are present in mouse atherosclerotic vessels and do equivalent transcriptional states exist in human coronary and carotid lesions?
- What marker genes define lesion-associated foamy/Trem2hi macrophages and major DC states (cDC1, cDC2, mreg-DC) in vascular tissue?
- Are major macrophage and DC transcriptional states conserved across diverse mouse atherosclerosis models and detectable in human lesions?

## Key findings
Integrated analysis of 12 mouse scRNA-seq datasets (22,852 mouse myeloid cells) and 3 human scRNA-seq datasets (11 patients: 4 coronary, 7 carotid) identified: (1) discrete macrophage populations in vessels—Lyve1+ aortic resident macrophages, Il1b+ inflammatory macrophages, and Trem2hi foamy macrophages characterized by a conserved core signature (TREM2, SPP1, GPNMB, CD9); (2) transcriptomically distinct intimal resident macrophages versus lesion-associated Trem2hi macrophages; (3) conserved DC states including Xcr1+ cDC1, Cd209a+ cDC2, and Ccr7+/Fscn1+ mature/mreg-DC; and (4) these macrophage and DC states are conserved across mouse models and present in human lesions.

## Methods used
Per-dataset QC and metadata harmonization (including sex inference), Seurat v3 integrated data anchoring/batch-correction, joint clustering, marker-gene-based cell-type annotation, cross-species integration, marker-overlap analysis with InteractiVenn, Gene Ontology and transcription factor enrichment analyses, manual inspection of conserved gene programs.

## Method and dataset
Seurat v3 integration and clustering applied to droplet-based scRNA-seq datasets: 12 mouse aorta immune-cell datasets (combined 22,852 cells) from multiple models/conditions and 3 human lesion datasets covering 11 patients (4 coronary vessels, 7 carotid endarterectomies). Design: pooled multi-dataset integration with canonical marker-based annotation and cross-species mapping. Assumes that batch-correction can align heterogeneous protocols and that transcriptional clusters reflect biologically distinct cell states despite dissociation/dropout biases.

## Limitations
Heterogeneous, publicly deposited datasets with variable protocols, mouse models, and disease stages leading to potential residual batch effects; limited human sample number (11 patients) and lesion-only sampling (no PBMC); scRNA-seq technical limitations (dropout, dissociation bias) limiting sensitivity for some markers; absence of scATAC/chromatin or functional validation; plasmacytoid DC (pDC) marker definitions in human PBMC and scATAC-based TF evidence are missing.

## Evidence pattern
entity_definition; comparison_design: cross-dataset and cross-species integration (mouse vs human lesions); statistical_unit: single cells aggregated per cluster (22,852 mouse cells; human cells from 11 patients); metric: cluster marker gene expression and marker overlap (core gene signatures: TREM2, SPP1, GPNMB, CD9; XCR1, CD209a, CCR7, FSCN1); covariates: dataset origin, species, tissue site; validation: cross-species mapping and marker-overlap analyses; boundary_conditions: lesions/tissue-derived scRNA-seq, not peripheral blood or scATAC; analysis_used: Seurat v3 anchoring/integration, clustering, marker-gene annotation, InteractiVenn, GO and TF enrichment.

## Extends or contradicts
Extends prior single-cell studies that reported diverse myeloid states in atherosclerotic vessels by integrating multiple datasets and refining nomenclature; does not report contradictions to prior canonical definitions but refines and consolidates marker-based definitions across mouse and human lesion datasets.

## Boundary conditions
Works when: Applied to droplet-based scRNA-seq from vascular/lesion tissue samples aggregated across studies (total mouse myeloid cells ≈22k; human lesion samples from multiple patients), where Seurat v3 anchoring can correct batch effects and marker genes for macrophage/DC states are captured above dropout thresholds; works when tissue-resident myeloid states are present (coronary or carotid lesions) and sufficient cells per cluster exist for marker detection.
Fails when: Fails or is not applicable for peripheral blood PBMC analyses (blood-derived cell states not profiled here), for scATAC-only datasets (no chromatin accessibility analyses performed), for datasets with very low cell counts per condition (<~100 cells/cluster) or extremely divergent protocols producing uncorrectable batch effects, and when functional or regulatory (TF motif) validation is required (not provided).
