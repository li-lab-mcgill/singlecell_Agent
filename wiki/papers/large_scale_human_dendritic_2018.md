---
paper_id: large_scale_human_dendritic_2018
title: "Large-Scale Human Dendritic Cell Differentiation Revealing Notch-Dependent Lineage Bifurcation and Heterogeneity."
doi: "10.1016/j.celrep.2018.07.033"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC6113934/"
source_ids: {doc_id: "pmc:6113934", pmid: "30110645", pmcid: "6113934", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_cell_type_annotation", "rna_clustering", "rna_trajectory"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["Obtain marker definitions for DC subsets cDC1, cDC2, pDC in human PBMC by scRNA and scATAC"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
The paper presents a scalable feeder-based in vitro differentiation system from human CD34+ precursors that yields high numbers of pDCs, cDC1s and cDC2s. Using flow cytometry, functional assays and single-cell RNA-seq, the authors show DLL1-mediated Notch signaling (and cooperation with GM-CSF) drives cDC1 differentiation and identify subset marker genes and a pre-terminal cycling precursor state for each DC type.

## Hypothesis framed
DLL1-dependent Notch signaling and cooperating cytokines (e.g., GM-CSF) regulate lineage bifurcation of human CD34+ precursors such that DLL1 promotes cDC1 differentiation while inhibiting pDC generation.

## Questions answered
- Does Notch signaling via DLL1 promote cDC1 differentiation and inhibit pDC generation from human CD34+ precursors?
- Can an OP9/OP9_DLL1 feeder-based culture generate high yields of transcriptionally and functionally bona fide human pDCs, cDC1s, and cDC2s?
- Does GM-CSF cooperate with DLL1-dependent Notch signaling to increase human cDC1 output?

## Key findings
1) An OP9 + OP9_DLL1 feeder culture with FLT3L/TPO/IL-7 generates high yields of pDCs, cDC1s and cDC2s that phenotypically, functionally and transcriptionally resemble blood counterparts. 2) DLL1-dependent Notch signaling strongly promotes cDC1 differentiation and concomitantly inhibits pDC generation; mixed OP9/OP9_DLL1 feeders permit simultaneous generation of both lineages. 3) GM-CSF enhances DLL1-dependent cDC1 output. 4) Single-cell RNA-seq identified marker genes: cDC1 (XCR1, CLEC9A), cDC2 (CD1C, FCER1A), pDC (TCF4, CLEC4C), and revealed a pre-terminal cycling precursor state for each DC type; cDC1 precursors lacked XCR1 expression prior to terminal differentiation.

## Methods used
In vitro expansion and differentiation of human cord-blood CD34+ progenitors on OP9 and OP9_DLL1 stromal feeders with cytokines (FLT3L, SCF, TPO, IL-7, tested GM-CSF); flow cytometry phenotyping; functional assays (activation/cytokine responses); single-cell RNA-sequencing with clustering and trajectory analyses; comparisons to primary blood DCs.

## Method and dataset
Feeder-based differentiation protocol: expand cord-blood CD34+ cells 7 days with FLT3L/SCF/TPO/IL-7 then differentiate 18–21 days on OP9 / OP9_DLL1 feeders with FLT3L/TPO/IL-7 and tested GM-CSF. Data types: in vitro-derived cells and primary blood DCs assayed by flow cytometry, functional assays, and single-cell RNA-seq. Approximate dataset size not reported in the summary. Experimental design: feeder comparison (OP9 vs OP9_DLL1 vs mixed) and cytokine perturbations; single-cell transcriptomic profiling to define clusters, markers, and trajectories. Assumptions: feeder-based signals recapitulate key Notch and cytokine cues relevant to in vivo DC differentiation.

## Limitations
Feeder-based in vitro system may not fully recapitulate in vivo microenvironments; results may be influenced by culture conditions, donor variability, and cytokine doses; functional equivalence to in vivo DCs not exhaustively demonstrated across all immune functions or in vivo contexts; molecular mechanisms of Notch/GM-CSF cooperation not dissected; not demonstrated for clinical/GMP-scale production; no scATAC or chromatin-accessibility evidence provided.

## Evidence pattern
entity_definition, validation, comparison_design, controls_covariates, statistical_unit, boundary_conditions

## Extends or contradicts
Resolves prior conflicting reports about the role of Notch signaling in human pDC versus cDC development by demonstrating DLL1 promotes cDC1 and inhibits pDC; builds on prior CD34+ feeder-based DC differentiation protocols by combining OP9 and OP9_DLL1 feeders and testing GM-CSF effects.

## Boundary conditions
Works when: Applies to in vitro differentiation of human cord-blood CD34+ progenitors expanded 7 days with FLT3L/SCF/TPO/IL-7 and differentiated 18–21 days on OP9 and/or OP9_DLL1 feeders with FLT3L/TPO/IL-7; inclusion of DLL1 signal and supplementation with GM-CSF increases cDC1 yield; comparisons and validation performed against blood-derived DCs using flow cytometry, functional assays and scRNA-seq.
Fails when: Findings may not hold in absence of OP9/OP9_DLL1 feeder signals or when DLL1-mediated Notch signaling is absent; not validated for in vivo differentiation environments or other progenitor sources (e.g., adult peripheral blood CD34+ without optimization); does not provide scATAC/chromatin evidence so regulatory conclusions about marker loci cannot be made; performance untested under different cytokine regimes, different donor sources, or clinical/GMP production conditions.
