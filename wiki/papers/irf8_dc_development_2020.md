---
paper_id: irf8_dc_development_2020
title: "Differential IRF8 Transcription Factor Requirement Defines Two Pathways of Dendritic Cell Development in Humans."
doi: "10.1016/j.immuni.2020.07.003"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC7447982/"
source_ids: {doc_id: "pmc:7447982", pmid: "32735845", pmcid: "7447982", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_cell_type_annotation", "rna_trajectory", "rna_clustering"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["Obtain marker definitions for DC subsets cDC1, cDC2, pDC in human PBMC by scRNA and scATAC"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
Using high-dimensional cytometry, targeted transcriptomics and single-cell RNA-seq with diffusion mapping, the paper defines two distinct developmental pathways for human CD1c+ (cDC2-related) dendritic cell heterogeneity that differ in their requirement for IRF8. An allelic series of human IRF8 deficiency and in vitro differentiation validate that an IRF8hi lymphoid-primed pathway (CD123+, BTLA+) yields pDCs, cDC1 and DC2 (including AXL+SIGLEC6+ pre-DCs), while an IRF8lo myeloid pathway (SIRPA+) produces DC3s and monocytes.

## Hypothesis framed
Human CD1c+ DC heterogeneity arises from two distinct developmental pathways that differ in their requirement for IRF8 activity, such that an IRF8hi lymphoid-primed trajectory produces pDC, cDC1 and DC2, whereas an IRF8lo myeloid trajectory produces DC3 and monocytes.

## Questions answered
- Does CD1c+ (CD1c+) dendritic cell heterogeneity reflect distinct developmental trajectories with different IRF8 requirements?
- Which progenitor compartments (LMPP-derived CD123-enriched GMPs versus myeloid GMPs) give rise to DC2 versus DC3/monocyte lineages?
- Do AXL+ SIGLEC6+ pre-DCs map specifically to the DC2 developmental trajectory?

## Key findings
1) Defined two developmentally distinct CD1c+ DC pathways: a lymphoid-primed IRF8hi pathway (marked by CD123 and BTLA) that produces pDCs, cDC1 and DC2, and a common myeloid IRF8lo pathway (expressing SIRPA) that produces DC3s and monocytes. 2) AXL+SIGLEC6+ pre-DCs map exclusively to the IRF8hi/DC2 trajectory. 3) DC2 potential localized to LMPP-derived, CD123-enriched GMPs, whereas DC3/monocyte output derives from distinct myeloid progenitors. 4) Functionally, all CD1c+ fractions produced IL-12 upon TLR stimulation; CD14+CD1c+ cells additionally produced IL-1β and IL-10. 5) In an allelic series of human IRF8 deficiency, partial IRF8 deficiency selectively impairs the IRF8hi DC2 pathway and is associated with expansion of DC3s (which have lower IRF8 requirement).

## Methods used
High-dimensional flow and mass cytometry panels for antigen profiling; targeted transcriptomics (NanoString) on sorted fractions; unbiased single-cell RNA-seq with diffusion-map trajectory analysis; in vitro differentiation assays tuned to distinguish DC2 vs DC3 outputs; analysis of hematopoietic progenitors (LMPP and GMP compartments); study of human patients with an allelic series of IRF8 deficiency; intracellular cytokine staining after TLR stimulation.

## Method and dataset
Single-cell RNA-seq of human peripheral blood and progenitor populations (exact cell counts not reported in summary); targeted NanoString (n=3 reported for some assays); mass and flow cytometry panels profiling surface markers (CD1c, AXL, SIGLEC6, CD123, BTLA, SIRPA, CD14); in vitro differentiation cultures to assay DC outputs; allelic-series patient samples with different IRF8 genotypes. Design assumes that surface-marker-defined sorted populations correspond to transcriptional identities and that in vitro differentiation recapitulates in vivo lineage potential.

## Limitations
Small sample sizes for some assays (e.g., NanoString n=3); allelic series limited by available patients and may not represent full IRF8 dysfunction spectrum; lack of scATAC data and absence of explicit single-cell chromatin accessibility profiling; in vitro differentiation and marker-based trajectory inference may not fully recapitulate in vivo dynamics; overlap in surface markers between DCs and monocytes complicates gating definitions; functional assays limited to selected cytokine readouts; causal transcriptional mechanisms downstream of IRF8 not fully delineated.

## Evidence pattern
entity_definition (surface + scRNA markers defining DC subsets), validation (in vitro differentiation and human IRF8 allelic perturbations), comparison design (allelic series comparing partial deficiency to controls), statistical unit: cell populations and patient samples, metrics: marker expression, trajectory position, cytokine production (IL-12, IL-1β, IL-10), covariate: IRF8 genotype; analysis used: cytometry, NanoString, scRNA diffusion mapping and lineage tracing through progenitor compartments.

## Extends or contradicts
Extends prior observations that IRF8 differentially affects DC subsets and refines the origin of human CD1c+ DC heterogeneity by demonstrating two distinct IRF8-dependent developmental pathways and mapping AXL+SIGLEC6+ pre-DCs to the IRF8hi/DC2 trajectory.

## Boundary conditions
Works when: Applied to human peripheral blood and hematopoietic progenitor (LMPP and GMP) samples analyzed ex vivo and tested with in vitro differentiation; requires measurement of surface markers including CD1c, AXL, SIGLEC6, CD123, BTLA, SIRPA and CD14 and availability of IRF8 genotype information for perturbation analysis; trajectory inference relies on sufficient representation of progenitor compartments (LMPP/GMP).
Fails when: Findings do not apply when single-cell chromatin accessibility (scATAC) evidence is required, in non-human systems, or when samples lack progenitor populations or IRF8 genotype diversity; marker overlap between monocytes and DCs may prevent reliable subset assignment in datasets with high monocyte contamination or incomplete marker panels; conclusions about causality of downstream transcriptional programs may fail without direct mechanistic perturbation of IRF8 targets.
