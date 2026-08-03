---
paper_id: enhancer_driven_gene_regulatory_2025
title: "Enhancer-driven gene regulatory networks reveal transcription factors governing T cell adaptation and differentiation in the tumor microenvironment."
doi: "10.1016/j.immuni.2025.04.030"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12240711/"
source_ids: {doc_id: "pmc:12240711", pmid: "40425012", pmcid: "12240711", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multi_grn_inference", "atac_grn_inference", "multiomic_integration"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Determine computational method classes and failure modes for inferring transcription factor programs from single-cell ATAC or paired RNA+ATAC multiome data in cell-type-specific disease analyses."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
This study used paired single-cell RNA-seq and single-cell ATAC-seq of TCR-matched antigen-specific CD8+ T cells across infection and tumor models to infer enhancer-driven regulons controlling T cell states. It identified a regulatory axis in which KLF2 suppresses, while sustained BATF promotes, CD69+CD103+ Trm-like tumor-infiltrating lymphocyte formation and anti-tumor adaptation.

## Hypothesis framed
Enhancer-linked gene regulatory networks inferred from paired RNA and ATAC profiles can identify transcription factors that causally govern differentiation of CD8+ tumor-infiltrating lymphocytes into CD69+CD103+ tissue-resident-memory-like states in the tumor microenvironment.

## Questions answered
- Can enhancer-driven regulon analysis of paired RNA+ATAC data nominate transcription factors regulating Trm-like CD8+ TIL differentiation?
- Does KLF2 repress formation of CD69+CD103+ Trm-like tumor-infiltrating CD8+ T cells and limit anti-tumor activity?
- Can sustained BATF expression promote CD69+CD103+ TIL formation, including when TGFBR2 is silenced?

## Key findings
Trm-like TILs combined features of exhausted T cells from chronic infection and canonical tissue-resident memory T cells. Enhancer-driven regulatory network analysis nominated KLF2 as a negative regulator of CD69+CD103+ Trm-like TIL differentiation, and functional experiments showed that KLF2 limited Trm-like TIL formation and anti-tumor activity. Sustained BATF expression enhanced CD69+CD103+ TIL formation, but this required KLF2 downregulation. TGF-beta signaling and CD103 expression were necessary for normal Trm-like TIL formation, while BATF overexpression could still drive CD69+CD103+ TIL generation in TGFBR2-silenced cells.

## Methods used
Paired single-cell RNA sequencing and single-cell ATAC sequencing of antigen-specific CD8+ T cells; TCR-matched P14 CD8+ T cell comparison across acute infection, chronic infection, and engineered tumor models expressing LCMV GP33; comparison of naive, effector, memory, exhausted, tissue-resident, and tumor-infiltrating CD8+ T cell states; enhancer-driven regulon inference including SCENIC+; functional perturbation experiments targeting KLF2, BATF, TGF-beta signaling through TGFBR2, and CD103.

## Method and dataset
The study applied enhancer-driven regulon inference to paired scRNA-seq and scATAC-seq profiles from TCR-matched antigen-specific mouse CD8+ T cells isolated from acute infection, chronic infection, and multiple engineered tumor models expressing the same LCMV GP33 antigen. The approximate number of cells was not reported in the provided summary. The design assumes that matched RNA expression, chromatin accessibility, motif/enhancer information, and enhancer-gene links can identify transcription factor programs associated with specific T cell differentiation states.

## Limitations
The study was primarily performed in mouse engineered tumor models using a shared model antigen and TCR-transgenic P14 CD8+ T cells, which may not represent the diversity of endogenous human anti-tumor T cell responses. Human tumor validation and validation across more diverse antigen-specific settings remain needed. The inferred enhancer-driven regulons may not capture all causal regulatory interactions. The safety, durability, and therapeutic feasibility of manipulating BATF, KLF2, TGF-beta signaling, or CD103 were not established.

## Evidence pattern
The evidence used entity definition of CD69+CD103+ Trm-like TILs, comparison across acute infection, chronic infection, tumor-infiltrating, memory, exhausted, and tissue-resident CD8+ T cell states, paired multiomic RNA+ATAC profiling, enhancer-driven regulon inference including SCENIC+, and perturbation validation of nominated regulators KLF2 and BATF. Boundary-condition experiments tested dependence on TGF-beta signaling and CD103, including BATF overexpression in TGFBR2-silenced cells.

## Extends or contradicts
The study extends prior observations that CD8+ TILs with tissue-resident memory markers CD69 and CD103 are associated with improved outcomes in solid tumors by identifying KLF2 repression and sustained BATF activity as regulatory mechanisms influencing Trm-like TIL differentiation in mouse tumor models.

## Boundary conditions
Works when: The approach applies when paired scRNA-seq and scATAC-seq data are available from matched or comparable cell states, when the biological system contains distinguishable T cell differentiation states, and when enhancer accessibility, gene expression, and transcription factor motif information can be linked into enhancer-driven regulons. The biological findings were supported in mouse tumor and infection models using antigen-specific TCR-matched CD8+ T cells recognizing the same LCMV GP33 antigen.
Fails when: The regulatory conclusions may not generalize to human tumors, endogenous polyclonal T cell responses, tumor antigens other than the model GP33 antigen, or settings where TCR-transgenic P14 biology does not reflect endogenous anti-tumor immunity. The computational regulon inference may miss causal interactions or misassign enhancer-gene-TF relationships when ATAC signal is sparse, enhancer-gene linkage is incorrect, or TF motif similarity prevents unambiguous assignment, but these failure modes were not systematically benchmarked in the paper summary.
