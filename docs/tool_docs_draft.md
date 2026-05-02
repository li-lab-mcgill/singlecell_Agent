# Tool Documentation

This document is the tool reference passed to ToolConsultant.
Each tool lists: what it does, what it returns, parameters with defaults, and when to use it.

Planner contract for DAG plans:
- ToolConsultant chooses semantic parameters only in `dag_plan.layers[].variants[].params`.
- Do not include executor-managed keys in variant params: `input_h5ad_path`, `output_h5ad_path`, `output_dir`, or `method`.
- Put the selected method only in `variant.method`.
- DagExecutor supplies per-stage input/output paths and output directories, then exposes produced files through `resolved_outputs` and artifacts.

---

## Data Inspection Tools

### read_dataset_summary
Read the pre-computed dataset summary for the loaded h5ad. No arguments.
Returns: shape (n_cells x n_genes), X dtype/sparsity, obs columns and dtypes, var columns, layers, obsm/varm keys with shapes, uns keys, QC stats if present, ground truth label column, and an LLM-generated natural language summary.
Use when: the user asks for a data overview, dataset description, or "what's in the data."

### read_label_distribution
Read the value counts for an obs column (e.g. cell_type, batch).
Args: label_key* (string) — the obs column name.
Returns: category names with counts and proportions.
Use when: the user asks "how many cell types", "show the batch distribution", etc.

### read_prior_resource_summary
Read a structured summary of available prior resources (marker DBs, pathway DBs, reference atlases).
No arguments.
Returns: list of resource names, types, and coverage info.

### check_prior_coverage
Estimate how well a named prior resource covers the current dataset's genes.
Args: resource_name* (string).
Returns: coverage fraction, matched/unmatched gene counts.

### query_marker_database
Look up known marker genes from the local marker DB.
Args: tissue* (string), species* (string).
Returns: marker gene lists grouped by cell type.

### query_pathway_database
Look up pathway or GO entries for a gene symbol.
Args: database* ("msigdb" | "go"), gene* (string).
Returns: matching pathway/GO entries with descriptions.

---

## Reference Management Tools

### list_available_references
List static reference resources available to compute tools.
Args: category (optional, one of: genome, annotation, motifs, atlas, markers, intervals, pathways, tf_targets, ligand_receptor, model).
Returns: list of resource metadata dicts.

### get_reference_info
Get metadata for one reference resource (version, size, status, source URL).
Args: name* (string).
Returns: resource metadata dict.

### ensure_reference_loaded
Download (if needed) and parse a reference into memory. Use before a long pipeline to warm caches.
Args: name* (string).
Returns: {status: "ok"}.

---

## API Query Tools

### fetch_gene_info
Look up gene metadata from Ensembl by symbol.
Args: gene_symbol* (string), species (string, default "homo_sapiens").
Returns: location, aliases, description, biotype.

### fetch_motif_pwm
Fetch a motif PWM from JASPAR. Provide either motif_id or tf_symbol.
Args: motif_id (string), tf_symbol (string), species_tax_id (string).
Returns: PWM matrix and motif metadata.

### search_reference_atlas
Search CellxGene Discover for reference atlases.
Args: tissue (string), species (string), assay (string). All optional but provide at least one.
Returns: ranked list of candidate atlas datasets. Pass results into label transfer tools.

### fetch_pathway_members
Fetch gene members of a pathway from KEGG or Reactome.
Args: pathway_id* (string), database* ("kegg" | "reactome").
Returns: list of gene symbols in the pathway.

### fetch_protein_interactions
Fetch protein-protein interactions from STRING.
Args: gene_symbol* (string), species_tax_id (string, default "9606"), score_min (number 0-1, default 0.7).
Returns: interaction partners with confidence scores.

### fetch_disease_associations
Fetch disease associations from Open Targets.
Args: gene_symbol* (string).
Returns: associated diseases with scores.

### fetch_go_annotations
Fetch Gene Ontology annotations from QuickGO.
Args: gene_symbol* (string), ontology* ("molecular_function" | "biological_process" | "cellular_component"), species_tax_id (string, default "9606").
Returns: GO term annotations.

---

## RNA Compute Tools (Granular)

All granular RNA tools read an h5ad, process it, write a new h5ad.
Common runtime args: input_h5ad_path* (string), output_h5ad_path* (string). In DAG plans these are supplied by DagExecutor; do not include them in variant params.
Common return: {status, output_h5ad_path, method, n_cells, n_genes, available_embeddings}.
For clustering, embedding, annotation, or metric workflows, ToolConsultant should include conservative basic QC unless the user asks to skip QC or use raw/unfiltered data. Conservative basic QC defaults are min_genes=200, max_pct_mito=20.0, and min_cells=3; use max_pct_mito=5.0 only for explicitly stringent filtering.
Implementation guardrails: methods should validate required AnnData keys before running and validate expected outputs after running. Imputation/denoising tools write named layers and should not replace `adata.X` by default. Pseudobulk DE requires replicate/sample information.

### rna_quality_control
Filter cells and genes by QC metrics.
Args: method* ("basic" | "scrublet" | "scdblfinder" | "soupx" | "cellbender" | "emptydrops"), min_genes (int, default 200), max_pct_mito (number, default 20.0), min_cells (int, default 3), mt_pattern (string, default "^MT-"), expected_doublet_rate (number, default 0.06).
Methods:
- **basic** — Python/scanpy. Standard min_genes + pct_mito filtering. Default choice.
- **scrublet** — Python (scrublet). Doublet detection and removal.
- **scdblfinder** — **Requires R** (scDblFinder package). Runs `r_scripts/rna/doublet_scdblfinder.R`. **Not yet implemented.**
- **soupx** — **Requires R** (SoupX package). Runs `r_scripts/rna/ambient_soupx.R`. Ambient RNA removal. **Not yet implemented.**
- **cellbender** — Python CLI (cellbender). Ambient RNA removal via deep learning. **Not yet implemented.**
- **emptydrops** — **Requires R** (DropletUtils package). Runs `r_scripts/rna/empty_drops.R`. Statistical test for empty droplets. **Not yet implemented.**

### rna_normalization
Normalize expression values. Input should be raw counts.
Args: method* ("log1p" | "sctransform" | "scran"), target_sum (number, default 10000, only used by log1p).
Methods:
- **log1p** — Python/scanpy. normalize_total + log1p. Fast, standard default.
- **sctransform** — **Requires R** (Seurat package). Runs `r_scripts/rna/normalization_sctransform.R`. Regularized negative binomial regression that handles zero-inflation and variance stabilization. Preferred for 10x UMI data.
- **scran** — **Requires R** (scran + scater packages). Runs `r_scripts/rna/normalization_scran.R`. Pool-based size factor deconvolution followed by log-normalization. Robust for heterogeneous populations with varying library sizes.

### rna_feature_selection
Select highly variable genes. Methods: seurat_v3 (variance-stabilizing), cellranger (simplified dispersion), scanpy_hvg (scanpy default).
Args: method* ("seurat_v3" | "cellranger" | "scanpy_hvg"), n_top (int, default 2000), batch_key (string, optional — for batch-aware HVG selection).
Sets adata.var["highly_variable"]. Downstream tools (embed, cluster) automatically subset to HVGs.

### rna_dimensionality_reduction
Compute a latent embedding.
Args: method* ("pca" | "scvi" | "seurat_pca" | "scanvi"), n_pcs (int, default 50, PCA only), n_latent (int, default 30, scVI/scANVI), n_layers (int, default 2, scVI/scANVI), n_epochs (int, optional), batch_key (string, optional), label_key (string, required for scanvi), random_seed (int, default 42).
Writes to adata.obsm: X_pca, X_scvi, X_seurat_pca, or X_scanvi depending on method.
Methods:
- **pca** — Python/scanpy. Fast linear dimensionality reduction. Default choice for most workflows.
- **scvi** — Python (scvi-tools). Deep generative VAE. Use when batch correction is needed without a separate integration step.
- **seurat_pca** — **Requires R** (Seurat package). Runs `r_scripts/rna/dimreduction_seurat_pca.R`. NormalizeData → FindVariableFeatures → ScaleData → RunPCA. Writes to X_seurat_pca. Use when you want the Seurat preprocessing chain.
- **scanvi** — Python (scvi-tools). Semi-supervised variant of scVI. Requires label_key for known cell type labels.

### rna_batch_integration
Remove batch effects.
Args: method* ("harmony" | "liger" | "scvi" | "bbknn" | "scanorama"), batch_key* (string — obs column with batch labels), embedding_key (string, default "X_pca" — input embedding for harmony/bbknn/scanorama), n_pcs (int, default 50), n_latent (int, default 30), theta (number, default 2.0, harmony diversity penalty), n_epochs (int, optional).
Harmony, BBKNN, and Scanorama consume an existing embedding and default to X_pca; if embedding_key="X_pca" and PCA is missing, PCA is computed automatically. For a non-default embedding_key such as X_seurat_pca, that key must already exist in adata.obsm.
Methods:
- **harmony** — Python (harmonypy). Fast post-hoc correction on any embedding. Writes to X_harmony (or `{embedding_key}_harmony` for non-PCA input).
- **scvi** — Python (scvi-tools). VAE-based. Writes to X_scvi_integrated.
- **bbknn** — Python (bbknn). Graph-based, modifies the neighbor graph. No obsm output.
- **scanorama** — Python (scanorama). Panoramic stitching. Writes to X_scanorama (or `{embedding_key}_scanorama` for non-PCA input).
- **liger** — **Requires R** (rliger package). Runs `r_scripts/rna/batch_integration_liger.R`. NMF-based integration. **Not yet implemented.**

### rna_clustering
Cluster cells on a precomputed embedding. Methods: leiden (default, modularity-based), louvain (older alternative).
Args: embedding_key* (string — obsm key, e.g. "X_pca"), method ("leiden" | "louvain", default "leiden"), n_neighbors (int, default 15), resolution (number, default 1.0 — higher = more clusters), cluster_key (string, optional — obs column name for result), label_key (string, optional — if provided, computes NMI/ARI against this ground truth column).
Writes cluster labels to adata.obs[cluster_key]. Default cluster_key is "{prefix}_clusters" where prefix is embedding_key with "X_" stripped. Examples: embedding_key="X_pca" -> cluster_key="pca_clusters", embedding_key="X_seurat_pca" -> cluster_key="seurat_pca_clusters". If label_key given, also writes metrics to adata.uns.
Returns extra: {cluster_key, metrics: {ari, nmi, ...}}.

### rna_celltype_annotation
Annotate clusters with cell type labels. Requires clustering to be done first.
Args: method* ("gpt4" | "cellmarker" | "celltypist" | "singler" | "azimuth" | "scarches"), obs_cluster (string — cluster column to annotate), species (string), tissue_type (string), cancer_type (string, default "Normal"), model (string, default "Immune_All_Low.pkl", celltypist model), openai_api_key (string, gpt4 only), reference_atlas (string, scarches/singler/azimuth).
Methods:
- **gpt4** — Python. LLM-based marker interpretation. Requires openai_api_key.
- **cellmarker** — Python. Local marker database lookup.
- **celltypist** — Python (celltypist). Pretrained logistic regression classifier. Fast and automated.
- **singler** — **Requires R** (SingleR + celldex packages). Runs `r_scripts/rna/celltype_annotation_singler.R`. Reference-based annotation using correlation. **Not yet implemented.**
- **azimuth** — **Requires R** (Azimuth + SeuratData packages). Runs `r_scripts/rna/celltype_annotation_azimuth.R`. Seurat reference mapping with weighted nearest neighbors. **Not yet implemented.**
- **scarches** — Python (scarches). Deep reference mapping using pretrained scVI/scANVI model. **Not yet implemented.**

### rna_differential_expression
Compute DE genes grouped by an obs column.
Args: group_key* (string — obs column, usually cluster_key), method* ("wilcoxon" | "t" | "logreg" | "mast" | "edger_pseudobulk" | "deseq2_pseudobulk"), reference (string, default "rest" — compare each group vs rest or vs a specific group), sample_key (string, optional but recommended for pseudobulk — replicate/donor/sample column in obs), output_dir (string, optional), top_n (int, default 50).
Note: does NOT take output_h5ad_path. Returns DE result dict, optionally writes CSVs to output_dir.
Methods:
- **wilcoxon** — Python/scanpy. Fast nonparametric rank-sum test. Default for exploratory DE.
- **t** — Python/scanpy. Welch's t-test.
- **logreg** — Python/scanpy. Logistic regression classifier.
- **mast** — **Requires R** (MAST package). Runs `r_scripts/rna/differential_expression_mast.R`. Hurdle model for zero-inflated scRNA-seq data.
- **edger_pseudobulk** — **Requires R** (edgeR package). Runs `r_scripts/rna/differential_expression_edger_pseudobulk.R`. Pseudobulk DE for publication-quality results. Requires sample_key (replicate/donor column).
- **deseq2_pseudobulk** — **Requires R** (DESeq2 package). Runs `r_scripts/rna/differential_expression_deseq2_pseudobulk.R`. Pseudobulk DE. Requires sample_key (replicate/donor column).

### rna_2d_projection
Compute a 2D layout for visualization. Methods: umap, tsne, fa (Force Atlas).
Args: embedding_key* (string — obsm key to project from, e.g. "X_pca"), method* ("umap" | "tsne" | "fa"), n_neighbors (int, default 15, UMAP/FA only), random_seed (int, default 42).
Writes to adata.obsm: X_umap, X_tsne, or X_draw_graph_fa.
Run after dimensionality reduction. UMAP is the standard choice.

### rna_gene_program_inference [STUB]
Infer gene programs/modules. Methods: nmf, scenic, pagoda2, hotspot.
Args: method*, n_programs (int, default 20).
Implementation notes: start with NMF. NMF requires nonnegative expression and should avoid dense conversion on large sparse matrices. Store scores in `obsm["X_nmf"]`, loadings in `varm["nmf_loadings"]`, and top genes in `uns["gene_programs"]`.
NOT YET IMPLEMENTED — will raise NotImplementedError.

### rna_trajectory_inference [STUB]
Infer cell-state trajectories. Methods: paga, slingshot, monocle3, palantir.
Args: method*, embedding_key (string, optional), group_key (string, required for PAGA unless available from prior clustering).
Implementation notes: do not infer roots silently for pseudotime methods. PAGA requires a valid embedding and grouping column.
NOT YET IMPLEMENTED.

### rna_velocity [STUB]
Estimate RNA velocity. Methods: scvelo, velocyto, unitvelo.
Args: method*, spliced_key (string, default "spliced"), unspliced_key (string, default "unspliced"), mode ("stochastic" | "dynamical", default "stochastic"), n_pcs (int), n_neighbors (int).
Requires spliced/unspliced layers in the h5ad. Validate layers before running and record preprocessing/model params. NOT YET IMPLEMENTED.

### rna_perturbation_analysis [STUB]
Perturbation-response analysis. Methods: mixscape, gears, cpa.
Args: method*, perturbation_key* (string — obs column with perturbation labels).
NOT YET IMPLEMENTED.

### rna_imputation [STUB]
Impute/denoise expression. Methods: magic, saver, alra, dca.
Args: method*.
Implementation notes: imputation is for denoising/visualization unless explicitly requested for downstream analysis. Store output in layers such as `magic_imputed`; do not overwrite `adata.X`.
NOT YET IMPLEMENTED.

### rna_cell_cell_communication [STUB]
Infer cell-cell communication. Methods: cellchat, cellphonedb, liana.
Args: method*, group_key* (string), species* (string).
Note: does NOT take output_h5ad_path. Returns interaction result dict.
Implementation notes: require normalized/log expression, minimum cells per group, explicit species/resource mapping, and write a result table path in the returned object.
NOT YET IMPLEMENTED.

---

## RNA Composite Pipeline Tools

### rna_preprocess
End-to-end preprocessing: QC -> normalization -> HVG selection -> embedding.
Use for the standard happy-path workflow. If you need fine control over intermediate steps or want to inspect outputs between stages, use the granular tools instead.
Args: input_h5ad_path*, output_h5ad_path*, embed_method* ("pca" | "scvi" | "seurat_pca" | "scanvi"), min_genes (int, default 200), max_pct_mito (number, default 20.0), min_cells (int, default 3), normalize_method ("log1p" | "sctransform" | "scran", default "log1p"), target_sum (number, default 10000), feature_method ("seurat_v3" | "cellranger" | "scanpy_hvg", default "seurat_v3"), n_top_genes (int, default 2000), batch_key (string, optional), n_latent (int, default 30), n_epochs (int, optional), random_seed (int, default 42).
Returns: {status, output_h5ad_path, steps_run, n_cells_start, n_cells_after_qc, n_cells_removed, n_genes, available_embeddings, embed_method}.

### rna_cluster_and_annotate
End-to-end downstream: clustering -> DE -> cell type annotation.
Use after rna_preprocess for the standard downstream workflow. If you want to try multiple resolutions or compare annotation methods, use the granular tools instead.
Args: input_h5ad_path*, output_h5ad_path*, embedding_key* (string), annotate_method* ("gpt4" | "cellmarker" | "celltypist"), resolution (number, default 1.0), n_neighbors (int, default 15), label_key (string, optional — ground truth for metrics), de_method ("wilcoxon" | "t" | "logreg", default "wilcoxon"), species (string), tissue_type (string), cancer_type (string, default "Normal"), model (string, default "Immune_All_Low.pkl"), openai_api_key (string).
Returns: {status, output_h5ad_path, steps_run, cluster_key, n_clusters, cluster_metrics, de_summary, annotate_method}.

---

## ATAC Compute Tools

Most ATAC granular tools follow the same read-process-write pattern as RNA tools; result-only tools return typed result payloads.
ATAC implementation guardrails: methods must distinguish matrix-only workflows from fragment-level workflows. Coordinate-dependent methods require validated peak coordinates using either `var_names` in `chr:start-end` form or `var["chrom"]`, `var["start"]`, `var["end"]`. Fragment-level methods require `fragments_path` or `adata.uns["fragments_path"]`.

### atac_quality_control
scATAC QC. Implemented: basic, fragment_size summary. Not yet implemented: tss_enrichment, frip.
Args: method*, build ("hg38" | "mm10", default "hg38"), fragments_path (string, required for tss_enrichment/fragment_size/frip), min_counts, max_counts, min_features, min_cells.
Implementation notes: `basic` is matrix-count filtering. `fragment_size` accepts plain or gzipped 10x-style fragments and records global plus per-cell fragment summaries when barcodes match obs_names. TSS enrichment and FRiP are fragment-level QC and must not run from a peak matrix alone.

### atac_peak_calling
Call peaks from fragments. Implemented: macs2, macs3 via CLI. Not yet implemented: archr_iter, snapatac2.
Args: fragments_path* (string), output_peaks_path* (string), method*, genome_size ("hs" | "mm", default "hs"), q_value (number, default 0.05).
Note: takes fragments_path, NOT input_h5ad_path. 10x-style fragments are converted to BED for MACS; duplicate count columns are expanded before calling peaks.

### atac_feature_matrix_construction
Build or validate a cell x feature matrix. Implemented: peaks pass-through validation. Not yet implemented: tiles, bins.
Args: method*, peakset (string, optional), tile_size (int, default 500), fragments_path (string, required when building from fragments).
Implementation notes: pass-through `peaks` must validate genomic coordinates; `tiles`/`bins` require fragments and barcode alignment.

### atac_tfidf_lsi
TF-IDF normalization + LSI dimensionality reduction. Implemented: tfidf_lsi_v1, tfidf_lsi_v3. Not yet implemented: snapatac2_svd.
Args: method ("tfidf_lsi_v1" | "tfidf_lsi_v3" | "snapatac2_svd", default "tfidf_lsi_v3"), n_components (int, default 50), drop_first (bool, default true), binarize (bool, default true), random_seed (int), scale_factor (default 10000).
Writes to adata.obsm["X_lsi"].
Implementation notes: handle zero-count cells before TF-IDF, keep sparse matrices sparse, record explained variance and depth correlation. `tfidf_lsi_v3` uses log(TF) * log(IDF)-style weighting.

### atac_batch_integration
Remove batch effects in ATAC. Implemented: harmony on LSI. Not yet implemented: scvi_atac, liger_atac.
Args: method*, batch_key*, embedding_key (default "X_lsi"), theta (default 2.0).

### atac_clustering
Cluster on LSI embedding. Implemented: leiden, louvain.
Args: embedding_key*, method (default "leiden"), resolution (default 1.0), n_neighbors (default 15).

### atac_gene_activity_score [STUB]
Compute per-gene activity scores from peaks. Methods: cicero, archr, signac.
Args: method*, gene_annotation* ("gencode_v44_human" | "gencode_vM33_mouse").

### atac_motif_enrichment [STUB]
TF motif enrichment per cell/cluster. Methods: chromvar, homer.
Args: method*, motif_db* ("jaspar2024_core_vertebrates" | "cisbp_v2_human").

### atac_differential_accessibility
DE for peaks. Implemented: wilcoxon, logreg. Not yet implemented: edger_pseudobulk, deseq2_pseudobulk.
Args: input_h5ad_path*, group_key*, method*, output_dir (optional), top_n (default 50). No output_h5ad_path.
Implementation notes: wilcoxon/logreg are exploratory peak marker methods, require valid peak coordinates, and binarize accessibility by default. Use pseudobulk for condition-level inference with biological replicates.

### atac_peak_to_gene_linking
Link peaks to target genes. Implemented: peak2gene correlation against a gene-activity matrix. Not yet implemented: cicero, archr_p2g.
Args: input_h5ad_path*, method*, gene_annotation (default gencode_v44_human), max_distance (int, default 500000), gene_activity_key (default "gene_activity"), gene_names_key (default "genes"), gene_coordinates_key (default "gene_coordinates"), min_correlation (default 0.0), allow_negative (default false), min_abs_correlation (optional for allow_negative), top_n_per_gene (default 10), max_links_in_result (default 100), output_links_path (optional).
Implementation notes: require peak coordinates plus matched gene activity labels and gene coordinates. Positive peak-gene correlations are returned by default; output links table includes peak, gene, distance, and correlation when output_links_path is provided.

### atac_trajectory_inference
Trajectories on ATAC. Implemented: paga. Not yet implemented: slingshot.
Args: method*, embedding_key (default "X_lsi"), group_key (optional; defaults from clustering metadata), n_neighbors (default 15).

### atac_celltype_annotation
Annotate ATAC cell types. Implemented: marker_peaks. Not yet implemented: rna_label_transfer.
Args: method*, group_key (required for marker_peaks), marker_peak_sets (object mapping cell type to peak names or genomic intervals), annotation_key (optional), min_markers (default 1), reference_atlas (string, optional for future label transfer).

### atac_preprocess
End-to-end ATAC preprocessing: QC -> feature matrix -> TF-IDF + LSI.
Assumes peaks already called. Use atac_peak_calling first if starting from fragments.
Args: input_h5ad_path*, output_h5ad_path*, build ("hg38" | "mm10", default "hg38"), feature_method ("peaks" | "tiles" | "bins", default "peaks"), peakset (string, optional), tile_size (int, default 500), lsi_method (default "tfidf_lsi_v3"), n_components (int, default 50).
Also accepts fragments_path for fragment-derived feature construction, plus binarize and random_seed for TF-IDF/LSI.
Returns: {status, output_h5ad_path, steps_run, n_cells, n_features, available_embeddings}.

---

## Multimodal Tools

All are [STUB] — NOT YET IMPLEMENTED.
Multimodal implementation guardrails: paired RNA+ATAC methods require shared barcodes and consistent row order. Prefer MuData (`.h5mu`) for paired multimodal outputs. Do not concatenate RNA and ATAC cells as independent observations for paired methods. Validate feature overlap, peak coordinates, count layers, and reference resources before training.

### multi_paired_integration [STUB]
Integrate paired RNA + ATAC from the same cells. Methods: wnn, multivi, cobolt, scglue.
Args: rna_input_h5ad_path*, atac_input_h5ad_path*, output_h5ad_path*, method*, batch_key (optional).
Cells must share barcodes across modalities. Validate overlap and reorder before running. WNN requires RNA PCA and ATAC LSI or computes them internally. MultiVI requires count layers and correct modality registration; do not use naive AnnData concatenation.

### multi_mosaic_integration [STUB]
Integrate heterogeneous modality combinations. Methods: multigrate, stabmap, scmomat.
Args: input_paths* (array of h5ad paths, min 2), modalities* (array, e.g. ["rna", "atac"]), output_path*, method*.
For datasets where different samples have different modality combinations.
Implementation notes: validate `len(input_paths) == len(modalities)`, preserve sample/modality labels, and record missing modality pattern.

### multi_unpaired_integration [STUB]
Integrate unpaired RNA and ATAC. Methods: scglue, liger, seurat_cca.
Args: rna_input_h5ad_path*, atac_input_h5ad_path*, output_h5ad_path*, method*.
For separately profiled RNA and ATAC datasets.
Implementation notes: scGLUE requires RNA gene annotation, ATAC peak coordinates, and a guidance graph. Return modality labels and separate embeddings.

### multi_label_transfer [STUB]
Transfer labels from a reference atlas. Methods: scanvi, seurat_cca, scarches, celltypist.
Args: input_h5ad_path*, output_h5ad_path*, reference_atlas* (string), method*, modality ("rna" | "atac" | "both", default "rna").
Implementation notes: CellTypist is RNA/gene-activity based; raw ATAC peaks require gene activity or RNA label transfer. Validate feature/model overlap and store confidence scores.

### multi_cross_modality_prediction [STUB]
Predict one modality from another. Methods: babel, polarbear, scglue.
Args: input_h5ad_path*, output_h5ad_path*, source_modality* ("rna" | "atac"), target_modality* ("rna" | "atac"), method*.

### multi_joint_differential_expression [STUB]
Joint DE across RNA and ATAC. Methods: limma_voom, scanpy_joint, mast_joint.
Args: rna_input_h5ad_path*, atac_input_h5ad_path*, group_key*, method*, sample_key (recommended/required for condition inference).
Implementation notes: scanpy_joint is exploratory. Publication-grade condition testing requires replicate-aware methods.

### multi_joint_rna_velocity [STUB]
Joint RNA velocity with chromatin priors. Methods: multivelo, unitvelo_multi.
Args: rna_input_h5ad_path*, atac_input_h5ad_path*, output_h5ad_path*, method*.
Implementation notes: requires paired cells, RNA spliced/unspliced layers, ATAC peak coordinates, and a validated gene-peak linkage model.

### multi_grn_inference [STUB]
Gene regulatory network inference from paired RNA + ATAC. Methods: scenic_plus, figr, celloracle.
Args: rna_input_h5ad_path*, atac_input_h5ad_path*, output_edges_path*, method*, gene_annotation ("gencode_v44_human" | "gencode_vM33_mouse", default "gencode_v44_human").
Implementation notes: implement only after motif, genome, GTF, peak-to-gene, and external binary checks are in place. Provide a validation/dry-run mode before full training.

### multi_foundation_models [STUB]
Run a pretrained foundation model. Models: geneformer, scgpt, scfoundation. Tasks: embed, predict_celltype, perturbation_response.
Args: input_h5ad_path*, output_h5ad_path*, model*, task*.
Implementation notes: validate species, gene identifier type, tokenizer vocabulary coverage, model availability, and memory constraints before loading weights.

---

## Evaluation Tools

### evaluate_pipeline_result
Compute evaluation metrics on a processed h5ad WITHOUT re-running the pipeline.
Args: input_h5ad_path*, metrics* (array of: "silhouette", "ari", "nmi", "batch_entropy", "batch_lisi", "bio_lisi", "kbet", "marker_specificity"), embedding_key (string), cluster_key (string), label_key (string), batch_key (string), markers (object), objective_name (string).
Metric requirements:
- silhouette: needs embedding_key + (label_key or cluster_key)
- ari, nmi: needs cluster_key + label_key
- batch_entropy, batch_lisi, kbet: needs embedding_key + batch_key
- bio_lisi: needs embedding_key + label_key
Missing keys produce warnings, not errors. Request multiple metrics in one call.

---

## Paper / RAG Tools

### search_index
Semantic search over a RAG channel index.
Args: query* (string), channel* ("dataset" | "prior_resources" | "prior_methods" | "benchmark"), top_k (int 1-10, default 5).
Returns: ranked chunks with scores.

### read_paper_summary
Read the structured summary of a retrieved paper.
Args: paper_id* (string).
Returns: title, authors, abstract, key findings, methods used.

### fetch_paper_section
Fetch a specific section from a paper, returning top chunks if section is long.
Args: paper_id* (string), section_type* (string), top_n_chunks (int 1-5, default 3).
Returns: section text chunks ranked by relevance.
