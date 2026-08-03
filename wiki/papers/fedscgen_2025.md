---
paper_id: fedscgen_2025
title: "FedscGen: privacy-preserving federated batch effect correction of single-cell RNA sequencing data."
doi: "10.1186/s13059-025-03684-6"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12285155/"
source_ids: {doc_id: "pmc:12285155", pmid: "40696440", pmcid: "12285155", semantic_scholar_id: "", openalex_id: ""}
full_text_status: "pmc_xml"
tasks: ["rna_batch_correction", "multi_batch_correction"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["Find references defining kBET and LISI for assessing batch/mixing/integration quality of embeddings and neighbor graphs; report applicability to multi-omics modality-mixing assessment."]
extends: []
added: 2026-05-15
session: unknown
---

## Summary
FedscGen adapts the centralized scGen VAE model to a federated setting using secure multiparty computation (additive secret sharing) to enable privacy-preserving, communication-efficient batch effect correction for scRNA-seq. Benchmarked on eight datasets (including Human Pancreas), FedscGen matches centralized scGen on key batch-correction and cell-type preservation metrics while requiring modest communication (recommended default: 2 local epochs, 8 rounds) and is released as a FeatureCloud app.

## Hypothesis framed
A federated, secure aggregation adaptation of scGen (FedscGen) can achieve batch-correction performance comparable to centralized scGen on scRNA-seq data while preserving local data privacy and remaining communication-efficient.

## Questions answered
- Can a federated, privacy-preserving adaptation of scGen (FedscGen) match centralized scGen's batch-correction performance across diverse scRNA-seq datasets?
- What communication/local-training settings give a practical trade-off between privacy/efficiency and performance for federated scRNA-seq batch correction?

## Key findings
FedscGen achieved performance competitive with centralized scGen across eight benchmark datasets (including Human Pancreas) on metrics including NMI, ARI, ASW_B, ASW_C, KNN_Acc, kBET, LISI and EBM. The authors report a maximum performance drop of 0.07 relative to centralized scGen under their benchmarks. A recommended configuration of 2 local epochs and 8 communication rounds provided the best overall trade-off in hyperparameter sweeps. FedscGen was implemented as a FeatureCloud app and uses additive secret sharing for secure aggregation, but the aggregation scheme does not provide formal differential-privacy guarantees.

## Methods used
Federated training of local variational autoencoders (scGen-derived VAEs); secure multiparty computation via additive secret sharing for privacy-preserving model update aggregation; federated 'delta-vector' correction computed from mean latent features of shared cell types; benchmarking using metrics NMI, ARI, ASW_B, ASW_C, KNN_Acc, kBET, LISI, EBM; hyperparameter sweeps across communication rounds and local epochs; simulated client assignment by mapping each batch to a separate client.

## Method and dataset
FedscGen (federated scGen VAE with secure aggregation) applied to single-cell RNA-seq data across eight datasets (including the Human Pancreas dataset). Experimental design simulated heterogeneity by assigning each batch to a separate client and evaluated cell-level correction/preservation metrics. Assumptions: presence of shared cell types across sites for delta-vector calculation; availability of secure aggregation infrastructure; no formal differential privacy noise mechanism applied.

## Limitations
No single hyperparameter setting fits all datasets; evaluation used simulated client assignments which may not capture real-world heterogeneity; privacy relies on additive secret sharing (secure aggregation) without formal differential-privacy guarantees; additional computation and communication overhead from secure MPC; methodological details for metric computation (e.g., k selection, neighbor graph construction) and formal definitions of kBET/LISI are not provided; not evaluated on multimodal/multi-omics datasets or under stronger adversary/threat models.

## Evidence pattern
comparison_design; metrics: NMI, ARI, ASW_B, ASW_C, KNN_Acc, kBET, LISI, EBM; statistical unit: individual cells; covariates considered: batch and cell type; validation: benchmarking against centralized scGen across eight datasets with simulated client-per-batch assignment; analyses: hyperparameter sweeps (communication rounds, local epochs), secure aggregation experiments. The paper demonstrates practical use of kBET and LISI as effect metrics but does not provide algorithmic definitions or multi-omics applicability analysis.

## Extends or contradicts
Extends the centralized scGen VAE-based batch-correction approach by adapting it to a federated, privacy-preserving training and correction workflow (adds secure aggregation and federated delta-vector correction).

## Boundary conditions
Works when: Batches can be mapped to clients (one or few batches per client) and sites share at least one common annotated cell type to compute delta-vectors; datasets similar in scale and batch heterogeneity to the eight benchmarks used (including Human Pancreas); secure aggregation (additive secret sharing) is available; communication budget allows moderate rounds (e.g., ~8) and local epochs (e.g., ~2).
Fails when: No shared cell types exist across sites (precluding federated delta-vector computation); datasets are multimodal or multi-omics (method not evaluated for modality mixing); requirement for formal differential-privacy guarantees or stronger adversary models (additive secret sharing alone insufficient); extreme real-world client heterogeneity or severely constrained compute/communication budgets where MPC overhead is prohibitive.
