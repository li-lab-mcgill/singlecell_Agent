---
paper_id: chromvar_2017
title: "chromVAR: inferring transcription-factor-associated accessibility from single-cell epigenomic data."
doi: "10.1038/nmeth.4401"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC5623146/"
source_ids: {doc_id: "pmc:5623146", pmid: "28825706", pmcid: "5623146", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["atac_motif_analysis", "atac_clustering", "atac_grn_inference"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["Determine computational method classes and failure modes for inferring transcription factor programs from single-cell ATAC or paired RNA+ATAC multiome data in cell-type-specific disease analyses."]
extends: []
added: 2026-05-26
session: unknown
---

## Summary
chromVAR is an R package for sparse single-cell chromatin-accessibility data that estimates per-cell or per-sample accessibility deviations for peak sets sharing transcription factor motifs, k-mers, or genomic annotations. It corrects these deviations using matched background peaks controlled for GC content and average accessibility, producing deviation Z-scores for clustering cells and identifying transcription-factor-associated regulatory variation.

## Hypothesis framed
Aggregating sparse scATAC-seq counts across peaks that share motifs or annotations and correcting for GC content and average accessibility bias can recover biologically meaningful, transcription-factor-associated accessibility variation across cells.

## Questions answered
- Can sparse scATAC-seq peak counts be transformed into motif- or annotation-level per-cell accessibility scores that are robust enough for downstream analysis?
- Can bias-corrected accessibility deviation Z-scores identify known and de novo motifs associated with variation in chromatin accessibility?
- Can motif- or annotation-level chromVAR deviation scores support clustering of single-cell chromatin accessibility profiles?

## Key findings
chromVAR showed that sparse peak-level scATAC-seq counts can be converted into bias-corrected motif- or annotation-level accessibility deviation scores. The resulting deviation Z-scores supported accurate clustering of single-cell chromatin accessibility profiles and identified known and de novo sequence motifs associated with chromatin-accessibility variation. The summary does not report specific numerical performance values, cell counts, or benchmark effect sizes.

## Methods used
For each cell or sample, chromVAR computes observed fragments in peaks containing a motif, k-mer, or annotation and compares them with expected counts based on total accessibility per cell and mean accessibility of each peak across cells. It samples matched background peak sets to control for GC content and average peak accessibility, subtracts the mean background deviation, and scales by the background standard deviation to produce deviation Z-scores. These scores are used for cell clustering and motif or annotation association analyses.

## Method and dataset
Method: chromVAR deviation scoring on sparse chromatin accessibility count matrices from scATAC-seq or related ATAC-seq samples. Data type: fragments or counts over called accessibility peaks, with peak sets defined by transcription factor motifs, de novo motifs, k-mers, or genomic annotations. Approximate dataset size is not specified in the summary. The method assumes available peak calls, motif or annotation definitions, sufficient fragments per cell to estimate deviations, and that technical biases can be approximated by matching background peaks on GC content and average accessibility.

## Limitations
chromVAR infers transcription-factor-associated accessibility from motif enrichment and accessibility variation, but motif accessibility does not directly prove transcription factor binding or activity. Results depend on peak-call quality, motif database or annotation quality, and successful matching of background peaks for GC content and average accessibility. Very sparse or low-depth cells can produce noisy deviation estimates. Closely related transcription factors with similar DNA-binding motifs may be difficult to distinguish. The paper summary reports no direct benchmark against SCENIC+, EpiRegulon, or other multiome regulon inference methods and no integration of paired RNA expression with ATAC accessibility.

## Evidence pattern
Entity definition: defines chromVAR as motif-, k-mer-, or annotation-level accessibility deviation scoring for sparse scATAC-seq data. Statistical unit: cell or sample by motif/annotation deviation score. Effect metric: corrected deviation and deviation Z-score. Controls/covariates: matched background peak sets controlling GC content and average peak accessibility. Validation: use of deviation scores for clustering single-cell chromatin accessibility profiles and identifying known and de novo motifs associated with accessibility variation. Boundary conditions: applies to sparse scATAC-seq peak count matrices with motif or annotation peak sets; failure modes include low-depth cells, poor annotations, poor peak calls, and motif similarity among TF families.

## Extends or contradicts


## Boundary conditions
Works when: Works when the input is a scATAC-seq or ATAC-seq peak-by-cell count matrix with sufficient fragments per cell, reliable peak calls, and motif, k-mer, or genomic annotation sets that map peaks into biologically meaningful groups. It is designed for sparse chromatin-accessibility data where aggregating across motif- or annotation-sharing peaks improves signal over individual peak analysis. Bias correction is appropriate when matched background peaks can be sampled with similar GC content and average accessibility.
Fails when: May fail or become unreliable for extremely sparse or low-depth cells, poor-quality peak calls, incomplete or inaccurate motif databases or annotations, or datasets where matched background peaks do not adequately control GC content and average accessibility. It cannot distinguish TFs with highly similar motifs and cannot by itself prove TF binding, TF expression, TF activity, enhancer-gene regulation, or causal gene regulatory network edges. It does not directly use paired RNA expression and is not a full multiome regulon-inference method.
