---
paper_id: binarize_gene_expression_2025
title: "Facilitate integrated analysis of single cell multiomic data by binarizing gene expression values."
doi: "10.1038/s41467-025-60899-8"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12218346/"
source_ids: {doc_id: "pmc:12218346", pmid: "40595539", pmcid: "12218346", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["multiomic_integration", "rna_clustering", "atac_clustering"]
retrieval_goals: ["method_selection"]
retrieval_intents: ["What evidence supports TF-IDF normalization and LSI for scATAC-seq to mitigate sequencing depth/complexity confounding, and what boundary conditions/parameters are important?"]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
The paper shows that binarizing scRNA-seq (count>0 -> 1) and directly concatenating binary RNA with standard scATAC-seq matrices, followed by TF-IDF weighting and LSI (SVD), yields effective vertical integration and clustering for paired multiomic single-cell data. This approach removes the need to compute ATAC-derived gene-activity scores and allows direct assessment of each modality's contribution to cell identity.

## Hypothesis framed
Binarized scRNA-seq concatenated with scATAC-seq and analyzed with TF-IDF + LSI can produce accurate integrated clustering of paired multiomic single-cell data without converting ATAC peaks to gene-activity scores.

## Questions answered
- Can binarized scRNA-seq combined directly with scATAC-seq and analyzed by TF-IDF + LSI produce integrated clustering comparable to standard count-based RNA workflows?
- Does direct concatenation of binarized RNA + scATAC obviate computing gene-activity scores from ATAC for paired multiomic datasets?

## Key findings
Binarized scRNA-seq clustered comparably to quantitative count-based workflows when analyzed with TF-IDF + LSI; in PBMC data, overall >77% of cells within clusters were from a single annotated PBMC cell type and some clusters ranged 44–100% purity. Direct concatenation of binarized RNA and standard scATAC data followed by TF-IDF/LSI produced effective integrated clustering, eliminating the need to compute gene-activity scores. Some biologically similar cell types remained mixed or split (examples: CD4+ T subclusters, CD14 vs FCGR3A monocytes, CD8+ T vs NK).

## Methods used
Binarization of scRNA counts (value=1 if raw count>0 else 0); selection of top 2,000 highly variable genes based on binarized data; TF-IDF weighting; single-value decomposition / latent semantic indexing (LSI); concatenation of binary-RNA and scATAC matrices from paired multiomic experiments; dimensionality reduction to 30 PCs; Leiden clustering (resolution=1.0) via Scanpy; benchmarking with ARI, AMI, NMI, FMI, silhouette (scikit-learn v1.3.2) plus custom cluster accuracy and cell-type congregated score.

## Method and dataset
Applied TF-IDF + LSI to concatenated binary scRNA (binarized count matrix with top 2,000 HVGs) and standard scATAC peak-by-cell matrices from paired multiomic single-cell experiments. Datasets tested included a frequently used ~3k PBMC scRNA-seq dataset and a Smart-Seq2 human pancreatic dataset (paired RNA+ATAC). Experimental design: paired same-cell multiome measurements, clustering as primary evaluation. Assumptions: same-cell pairing available; binarization threshold raw count>0; TF-IDF appropriate for sparse binary and peak-count matrices; HVG selection on binarized data is informative.

## Limitations
Evaluation limited to a few datasets/platforms (PBMC and Smart-Seq2 pancreas) and to clustering as the readout; requires paired multiomic measurements (same-cell RNA+ATAC) for direct concatenation; no systematic analysis demonstrating TF-IDF/IDF reduces sequencing-depth or library-complexity confounding; lack of mathematical details for TF-IDF/IDF implementation; sensitivity to parameter choices (HVG selection, number of PCs, Leiden resolution); not tested across broad tissues, continuous trajectories, rare cell types, or strong batch effects; some similar cell types remain mixed/split.

## Evidence pattern
comparison_design; statistical_unit=cells from paired multiomic experiments; metrics=ARI, AMI, NMI, FMI, silhouette, plus custom cluster accuracy and cell-type congregated score; validation=external/internal benchmarking on PBMC (~3k) and Smart-Seq2 pancreas datasets; analysis used=TF-IDF weighting, LSI (SVD), Scanpy pipeline (30 PCs, Leiden res=1.0); boundary_conditions reported (top 2,000 HVGs, 30 PCs, Leiden resolution=1.0).

## Extends or contradicts
Extends prior observations that binary on/off gene calls can capture biologically meaningful structure in sparse single-cell data and builds on use of TF-IDF/LSI for scATAC-style data by demonstrating these tools work on concatenated binary RNA+ATAC; does not contradict standard count-based workflows but offers a simpler integration alternative that avoids ATAC->gene activity conversion.

## Boundary conditions
Works when: Works on paired same-cell multiomic datasets where both RNA and ATAC are measured in the same cells (tested on PBMC ~3k and Smart-Seq2 pancreas); binarization uses raw count>0; HVG selection of top 2,000 genes on binarized data; downstream TF-IDF + LSI with 30 PCs and Leiden clustering (resolution=1.0) produced performant clustering for distinct cell types and moderate dataset sizes where co-detection (sparse on/off signal) exists.
Fails when: Not validated for unpaired RNA and ATAC datasets; likely to fail or have reduced performance for rare cell types, complex continuous cell-state trajectories, tissues/platforms not tested, strong batch effects, datasets with extreme sequencing-depth or library-complexity variation (no direct evidence TF-IDF removes these confounders provided), and for resolving very fine-grained or highly similar subtypes (e.g., CD4 subclusters, CD14 vs FCGR3A monocytes, CD8 vs NK) without further parameter tuning.
