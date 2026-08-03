# Tools Overview

This overview reflects the current file-based tool registry under `backend/tools`.

Status definitions:

- **Implemented**: a registered tool file exposes a real `run()` implementation.
- **Not implemented**: a registered tool exists but raises `NotImplementedError`.
- Some implemented tools still require optional runtime dependencies such as R packages, scVI, MACS, pySCENIC, MOFA, or OpenAI credentials.

Current registry totals:

| Category | Registered | Implemented | Not implemented |
|---|---:|---:|---:|
| RNA | 33 | 30 | 3 |
| ATAC | 16 | 16 | 0 |
| Multiomics | 8 | 8 | 0 |
| Evaluation | 4 | 4 | 0 |

## RNA Tools

| Stage | Implemented tools | Not implemented / missing |
|---|---|---|
| QC | `rna_qc_basic`, `rna_qc_scrublet` | none |
| Normalize | `rna_normalize_log1p`, `rna_normalize_scran` | `sctransform` is not in the current registry |
| Feature selection | `rna_feature_selection_cellranger`, `rna_feature_selection_scanpy_hvg`, `rna_feature_selection_seurat_v3` | none |
| Embedding | `rna_embed_pca`, `rna_embed_scvi`, `rna_embed_scanvi`, `rna_embed_seurat_pca` | none |
| Batch integration | `rna_batch_integration_bbknn`, `rna_batch_integration_harmony`, `rna_batch_integration_scanorama` | none |
| Clustering | `rna_cluster_leiden`, `rna_cluster_louvain` | none |
| Projection | `rna_project_umap`, `rna_project_tsne` | none |
| Differential expression | `rna_de_wilcoxon`, `rna_de_ttest`, `rna_de_mast`, `rna_de_edger`, `rna_de_deseq2` | none |
| Annotation | `rna_annotate_cellmarker`, `rna_annotate_celltypist`, `rna_annotate_gpt4` | `rna_annotate_azimuth`, `rna_annotate_scarches`, `rna_annotate_singler` |
| GRN | `rna_grn_decoupler`, `rna_grn_grnboost2`, `rna_grn_pyscenic`, `rna_grn_pyscenic_aucell` | `download_databases.py` exists but is not a registered tool |

## ATAC Tools

| Stage | Implemented tools | Not implemented / missing |
|---|---|---|
| QC | `atac_qc_basic`, `atac_qc_fragment_size` | none |
| Peak calling | `atac_peak_calling_macs2`, `atac_peak_calling_macs3` | none |
| Feature selection | `atac_feature_selection_peaks` | none |
| Embedding | `atac_embed_lsi` | none |
| Topic modeling | `atac_topic_pycisTopic` | none |
| Batch integration | `atac_batch_integration_harmony` | none |
| Clustering | `atac_cluster_leiden`, `atac_cluster_louvain` | none |
| Projection | `atac_project_umap` | none |
| Differential accessibility | `atac_da_wilcoxon` | none |
| Annotation | `atac_annotate_gene_activity`, `atac_annotate_marker_peaks` | none |
| Motif | `atac_motif_enrichment` | none |
| Peak-to-gene | `atac_peak_to_gene_correlation` | none |

## Multiomics Tools

| Stage | Implemented tools | Not implemented / missing |
|---|---|---|
| QC | `multi_qc_intersect` | none |
| Embedding / integration | `multi_embed_mofa`, `multi_embed_multivi`, `multi_embed_wnn` | none |
| GRN / regulatory links | `multi_grn_peak_to_gene`, `multi_grn_pycistarget`, `multi_grn_scenicplus`, `multi_grn_scenicplus_aucell` | none |
| Annotation / clustering / projection | none registered | directories exist, but no tools are registered |

## Evaluation Tools

| Stage | Implemented tools | Not implemented / missing |
|---|---|---|
| Evaluation | `eval_ari_nmi`, `eval_silhouette`, `eval_ilisi_clisi`, `eval_kbet` | none |

## Registered Placeholders

The following tools are present in the registry but intentionally raise `NotImplementedError`:

| Tool | Notes |
|---|---|
| `rna_annotate_azimuth` | TODO: Azimuth via R runner / Seurat reference mapping |
| `rna_annotate_scarches` | TODO: scArches reference mapping with pretrained reference model |
| `rna_annotate_singler` | TODO: SingleR via R runner |
