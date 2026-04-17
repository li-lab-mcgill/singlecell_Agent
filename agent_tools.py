from __future__ import annotations

from typing import Any

from agent_tool_base import AgentTool, AgentToolRegistry, MultiToolBase


class ReadDatasetSummary(AgentTool):
    name = "read_dataset_summary"
    description = "Read the dataset summary and top-level task metadata."
    parameters = {"type": "object", "properties": {}, "additionalProperties": False}

    def __init__(self, store: Any):
        self.store = store

    def run(self, **kwargs: Any) -> Any:
        return self.store.read_dataset_summary()


class ReadLabelDistribution(AgentTool):
    name = "read_label_distribution"
    description = "Read the label distribution for a dataset annotation column such as cell_type or batch."
    parameters = {
        "type": "object",
        "properties": {"label_key": {"type": "string"}},
        "required": ["label_key"],
        "additionalProperties": False,
    }

    def __init__(self, store: Any):
        self.store = store

    def run(self, **kwargs: Any) -> Any:
        return self.store.read_label_distribution(kwargs["label_key"])


class ReadPriorResourceSummary(AgentTool):
    name = "read_prior_resource_summary"
    description = "Read the structured summary of available prior resources."
    parameters = {"type": "object", "properties": {}, "additionalProperties": False}

    def __init__(self, store: Any):
        self.store = store

    def run(self, **kwargs: Any) -> Any:
        return self.store.read_prior_resource_summary()


class CheckPriorCoverage(AgentTool):
    name = "check_prior_coverage"
    description = "Estimate how well a named prior resource covers the current dataset genes."
    parameters = {
        "type": "object",
        "properties": {"resource_name": {"type": "string"}},
        "required": ["resource_name"],
        "additionalProperties": False,
    }

    def __init__(self, store: Any):
        self.store = store

    def run(self, **kwargs: Any) -> Any:
        return self.store.check_prior_coverage(kwargs["resource_name"])


class SearchIndex(AgentTool):
    name = "search_index"
    description = "Semantic search over one RAG channel index."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "channel": {"type": "string", "enum": ["dataset", "prior_resources", "prior_methods", "benchmark"]},
            "top_k": {"type": "integer", "minimum": 1, "maximum": 10},
        },
        "required": ["query", "channel"],
        "additionalProperties": False,
    }

    def __init__(self, store: Any):
        self.store = store

    def run(self, **kwargs: Any) -> Any:
        return self.store.search_index(
            query=kwargs["query"],
            channel=kwargs["channel"],
            top_k=kwargs.get("top_k", 5),
        )


class ReadPaperSummary(AgentTool):
    name = "read_paper_summary"
    description = "Read the structured summary of a retrieved paper."
    parameters = {
        "type": "object",
        "properties": {"paper_id": {"type": "string"}},
        "required": ["paper_id"],
        "additionalProperties": False,
    }

    def __init__(self, store: Any):
        self.store = store

    def run(self, **kwargs: Any) -> Any:
        return self.store.read_paper_summary(kwargs["paper_id"])


class FetchPaperSection(AgentTool):
    name = "fetch_paper_section"
    description = "Fetch a specific paper section, returning top chunks when the section is long."
    parameters = {
        "type": "object",
        "properties": {
            "paper_id": {"type": "string"},
            "section_type": {"type": "string"},
            "top_n_chunks": {"type": "integer", "minimum": 1, "maximum": 5},
        },
        "required": ["paper_id", "section_type"],
        "additionalProperties": False,
    }

    def __init__(self, store: Any):
        self.store = store

    def run(self, **kwargs: Any) -> Any:
        return self.store.fetch_paper_section(
            paper_id=kwargs["paper_id"],
            section_type=kwargs["section_type"],
            top_n_chunks=kwargs.get("top_n_chunks", 3),
        )


class QueryMarkerDatabase(AgentTool):
    name = "query_marker_database"
    description = "Read known marker genes by tissue and species from the local marker database."
    parameters = {
        "type": "object",
        "properties": {
            "tissue": {"type": "string"},
            "species": {"type": "string"},
        },
        "required": ["tissue", "species"],
        "additionalProperties": False,
    }

    def __init__(self, store: Any):
        self.store = store

    def run(self, **kwargs: Any) -> Any:
        return self.store.query_marker_database(tissue=kwargs["tissue"], species=kwargs["species"])


class QueryPathwayDatabase(AgentTool):
    name = "query_pathway_database"
    description = "Look up pathway or GO entries associated with a gene symbol."
    parameters = {
        "type": "object",
        "properties": {
            "database": {"type": "string", "enum": ["msigdb", "go"]},
            "gene": {"type": "string"},
        },
        "required": ["database", "gene"],
        "additionalProperties": False,
    }

    def __init__(self, store: Any):
        self.store = store

    def run(self, **kwargs: Any) -> Any:
        return self.store.query_pathway_database(database=kwargs["database"], gene=kwargs["gene"])


class BatchIntegration(AgentTool):
    name = "batch_integration"
    description = (
        "Apply one or more batch-integration methods to a single-cell AnnData file. "
        "Use this when batches are already present in obs and you want integrated embeddings "
        "such as Harmony, LIGER, or scVI written back to a new h5ad file."
    )
    parameters = {
        "type": "object",
        "properties": {
            "input_h5ad_path": {
                "type": "string",
                "description": "Path to the input h5ad file to integrate.",
            },
            "output_h5ad_path": {
                "type": "string",
                "description": "Path where the integrated h5ad file should be written.",
            },
            "batch_key": {
                "type": "string",
                "description": "obs column containing batch labels.",
            },
            "methods": {
                "type": "array",
                "items": {"type": "string", "enum": ["harmony", "liger", "scvi"]},
                "minItems": 1,
                "uniqueItems": True,
                "description": "Batch-integration methods to run. Defaults to ['liger'] if omitted.",
            },
        },
        "required": ["input_h5ad_path", "output_h5ad_path", "batch_key"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        methods = kwargs.get("methods") or ["liger"]
        return self.backend.batch_integration(
            input_h5ad_path=kwargs["input_h5ad_path"],
            output_h5ad_path=kwargs["output_h5ad_path"],
            batch_key=kwargs["batch_key"],
            methods=methods,
        )


class PreprocessSingleCell(AgentTool):
    name = "preprocess_singlecell"
    description = (
        "Preprocess a single-cell AnnData file for RNA or ATAC modality. "
        "For RNA, this performs QC, normalization, HVG selection, scaling, and PCA. "
        "For ATAC, this performs QC, feature filtering, TF-IDF normalization, and LSI."
    )
    parameters = {
        "type": "object",
        "properties": {
            "input_h5ad_path": {
                "type": "string",
                "description": "Path to the input h5ad file.",
            },
            "output_h5ad_path": {
                "type": "string",
                "description": "Path where the processed h5ad file should be written.",
            },
            "modality": {
                "type": "string",
                "enum": ["rna", "atac"],
                "description": "Modality to preprocess. Use 'rna' for scRNA-seq or 'atac' for scATAC-seq.",
            },
            "batch_key": {
                "type": "string",
                "description": "Optional obs column for batch-aware RNA HVG selection.",
            },
            "min_genes": {"type": "integer", "minimum": 0, "description": "Minimum detected genes per cell for RNA QC."},
            "max_pct_mito": {"type": "number", "minimum": 0, "description": "Maximum mitochondrial percentage allowed per cell for RNA QC."},
            "min_cells": {"type": "integer", "minimum": 0, "description": "Minimum cells per feature/gene to retain it."},
            "n_top_genes": {"type": "integer", "minimum": 1, "description": "Number of highly variable genes to keep for RNA."},
            "target_sum": {"type": "number", "exclusiveMinimum": 0, "description": "Target library size for RNA normalization."},
            "n_pcs": {"type": "integer", "minimum": 1, "description": "Number of PCA components for RNA."},
            "min_features": {"type": "integer", "minimum": 0, "description": "Minimum accessible features per cell for ATAC QC."},
            "max_features": {"type": "integer", "minimum": 0, "description": "Maximum accessible features per cell for ATAC QC."},
            "n_top_features": {"type": "integer", "minimum": 1, "description": "Number of top accessible ATAC features to keep."},
            "n_components": {"type": "integer", "minimum": 1, "description": "Number of latent LSI components for ATAC before dropping depth component."},
        },
        "required": ["input_h5ad_path", "output_h5ad_path", "modality"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        import scanpy as sc

        adata = sc.read_h5ad(kwargs["input_h5ad_path"])
        adata = self.backend.preprocess_singlecell(
            adata,
            modality=kwargs["modality"],
            batch_key=kwargs.get("batch_key"),
            min_genes=kwargs.get("min_genes", 200),
            max_pct_mito=kwargs.get("max_pct_mito", 5.0),
            min_cells=kwargs.get("min_cells", 3),
            n_top_genes=kwargs.get("n_top_genes", 2000),
            target_sum=kwargs.get("target_sum", 1e4),
            n_pcs=kwargs.get("n_pcs", 50),
            min_features=kwargs.get("min_features", 500),
            max_features=kwargs.get("max_features", 50000),
            n_top_features=kwargs.get("n_top_features", 30000),
            n_components=kwargs.get("n_components", 50),
        )
        adata.write_h5ad(kwargs["output_h5ad_path"])
        return {
            "status": "ok",
            "input_h5ad_path": kwargs["input_h5ad_path"],
            "output_h5ad_path": kwargs["output_h5ad_path"],
            "modality": kwargs["modality"],
            "n_cells": int(adata.n_obs),
            "n_genes": int(adata.n_vars),
            "available_embeddings": sorted(list(adata.obsm.keys())),
        }


class RunEmbedding(AgentTool):
    name = "run_embedding"
    description = (
        "Compute a latent embedding for a single-cell AnnData file using scVI or Seurat. "
        "Use scVI for a deep generative latent space or Seurat for PCA-based embedding via R."
    )
    parameters = {
        "type": "object",
        "properties": {
            "input_h5ad_path": {
                "type": "string",
                "description": "Path to the input h5ad file.",
            },
            "output_h5ad_path": {
                "type": "string",
                "description": "Path where the updated h5ad file should be written.",
            },
            "method": {
                "type": "string",
                "enum": ["scvi", "seurat"],
                "description": "Embedding backend to run.",
            },
            "batch_key": {
                "type": "string",
                "description": "Optional obs batch column. Used by scVI directly and by Seurat to trigger integration.",
            },
            "n_latent": {"type": "integer", "minimum": 1, "description": "Latent dimension for scVI."},
            "n_layers": {"type": "integer", "minimum": 1, "description": "Number of hidden layers for scVI."},
            "n_epochs": {"type": "integer", "minimum": 1, "description": "Maximum training epochs for scVI. If omitted, scVI uses its default schedule."},
            "n_pcs": {"type": "integer", "minimum": 1, "description": "Number of principal components for Seurat PCA."},
            "random_seed": {"type": "integer", "description": "Random seed for embedding reproducibility."},
        },
        "required": ["input_h5ad_path", "output_h5ad_path", "method"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        import scanpy as sc

        adata = sc.read_h5ad(kwargs["input_h5ad_path"])
        adata = self.backend.run_embedding(
            adata,
            method=kwargs["method"],
            batch_key=kwargs.get("batch_key"),
            n_latent=kwargs.get("n_latent", 30),
            n_layers=kwargs.get("n_layers", 2),
            n_epochs=kwargs.get("n_epochs"),
            n_pcs=kwargs.get("n_pcs", 50),
            random_seed=kwargs.get("random_seed", 42),
        )
        adata.write_h5ad(kwargs["output_h5ad_path"])
        return {
            "status": "ok",
            "input_h5ad_path": kwargs["input_h5ad_path"],
            "output_h5ad_path": kwargs["output_h5ad_path"],
            "method": kwargs["method"],
            "available_embeddings": sorted(list(adata.obsm.keys())),
        }


class ClusterAndEvaluate(AgentTool):
    name = "cluster_and_evaluate"
    description = (
        "Run graph construction, Leiden clustering, differential expression, and UMAP using a precomputed embedding "
        "already stored in adata.obsm, and compute clustering metrics such as silhouette and optional label-based NMI/ARI."
    )
    parameters = {
        "type": "object",
        "properties": {
            "input_h5ad_path": {
                "type": "string",
                "description": "Path to the input h5ad file.",
            },
            "output_h5ad_path": {
                "type": "string",
                "description": "Path where the clustered h5ad file should be written.",
            },
            "embedding_key": {
                "type": "string",
                "description": "Key in adata.obsm to use for neighbor graph construction, such as X_scvi or X_seurat.",
            },
            "n_neighbors": {"type": "integer", "minimum": 1, "description": "Number of neighbors in the graph."},
            "resolution": {"type": "number", "exclusiveMinimum": 0, "description": "Leiden clustering resolution."},
            "cluster_key": {"type": "string", "description": "Optional obs column name for the output cluster labels."},
            "deg_method": {"type": "string", "description": "Differential expression method passed to scanpy rank_genes_groups."},
            "label_key": {"type": "string", "description": "Optional obs column with reference labels for NMI and ARI computation."},
        },
        "required": ["input_h5ad_path", "output_h5ad_path", "embedding_key"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        import scanpy as sc

        adata = sc.read_h5ad(kwargs["input_h5ad_path"])
        adata = self.backend.cluster_and_evaluate(
            adata,
            embedding_key=kwargs["embedding_key"],
            n_neighbors=kwargs.get("n_neighbors", 15),
            resolution=kwargs.get("resolution", 1.0),
            cluster_key=kwargs.get("cluster_key"),
            deg_method=kwargs.get("deg_method", "wilcoxon"),
            label_key=kwargs.get("label_key"),
        )
        adata.write_h5ad(kwargs["output_h5ad_path"])
        cluster_key = kwargs.get("cluster_key") or f"{kwargs['embedding_key'].replace('X_', '')}_clusters"
        return {
            "status": "ok",
            "input_h5ad_path": kwargs["input_h5ad_path"],
            "output_h5ad_path": kwargs["output_h5ad_path"],
            "embedding_key": kwargs["embedding_key"],
            "cluster_key": cluster_key,
            "available_embeddings": sorted(list(adata.obsm.keys())),
            "metrics": adata.uns.get(f"{cluster_key}_metrics", {}),
        }


class CellTypeAnnotation(AgentTool):
    name = "celltype_annotation"
    description = (
        "Annotate cluster labels with cell types using either GPT-4-based marker interpretation or the local CellMarker reference. "
        "Use this after clustering when obs already contains a cluster column."
    )
    parameters = {
        "type": "object",
        "properties": {
            "input_h5ad_path": {
                "type": "string",
                "description": "Path to the input h5ad file.",
            },
            "output_h5ad_path": {
                "type": "string",
                "description": "Path where the annotated h5ad file should be written.",
            },
            "obs_cluster": {
                "type": "string",
                "description": "obs column containing cluster assignments to annotate.",
            },
            "method": {
                "type": "string",
                "enum": ["gpt4", "cellmarker"],
                "description": "Annotation strategy to use.",
            },
            "species": {"type": "string", "description": "Species metadata used to filter marker references or guide GPT prompting."},
            "tissue_type": {"type": "string", "description": "Tissue metadata used to filter marker references or guide GPT prompting."},
            "cancer_type": {"type": "string", "description": "Cancer or normal context used for annotation filtering."},
            "openai_api_key": {"type": "string", "description": "Optional API key override for GPT-based annotation."},
        },
        "required": ["input_h5ad_path", "output_h5ad_path", "obs_cluster"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        return self.backend.celltype_annotation(
            input_h5ad_path=kwargs["input_h5ad_path"],
            output_h5ad_path=kwargs["output_h5ad_path"],
            obs_cluster=kwargs["obs_cluster"],
            method=kwargs.get("method", "gpt4"),
            species=kwargs.get("species", ""),
            tissue_type=kwargs.get("tissue_type", ""),
            cancer_type=kwargs.get("cancer_type", "Normal"),
            openai_api_key=kwargs.get("openai_api_key"),
        )


class PaperToolkit(MultiToolBase):
    """Toolkit exposing dataset, RAG, marker, and pathway evidence tools."""

    toolkit_name = "paper"
    brief_description = "Tools for dataset inspection and literature-backed evidence retrieval."

    def __init__(self, store: Any):
        self.store = store

    def register_tools(self, registry: AgentToolRegistry) -> AgentToolRegistry:
        return (
            registry
            .register(ReadDatasetSummary(self.store))
            .register(ReadLabelDistribution(self.store))
            .register(ReadPriorResourceSummary(self.store))
            .register(CheckPriorCoverage(self.store))
            .register(SearchIndex(self.store))
            .register(ReadPaperSummary(self.store))
            .register(FetchPaperSection(self.store))
            .register(QueryMarkerDatabase(self.store))
            .register(QueryPathwayDatabase(self.store))
        )


class SingleCellSequencingToolkit(MultiToolBase):
    """Placeholder toolkit for future single-cell analysis and Seurat-backed tools."""

    toolkit_name = "single_cell_sequencing"
    brief_description = "A series of methods for single-cell RNA sequencing data analysis."

    def __init__(self, backend: Any | None = None):
        self.backend = backend

    def register_tools(self, registry: AgentToolRegistry) -> AgentToolRegistry:
        if self.backend is not None:
            if hasattr(self.backend, "preprocess_singlecell"):
                registry.register(PreprocessSingleCell(self.backend))
            if hasattr(self.backend, "run_embedding"):
                registry.register(RunEmbedding(self.backend))
            if hasattr(self.backend, "cluster_and_evaluate"):
                registry.register(ClusterAndEvaluate(self.backend))
            if hasattr(self.backend, "celltype_annotation"):
                registry.register(CellTypeAnnotation(self.backend))
            if hasattr(self.backend, "batch_integration"):
                registry.register(BatchIntegration(self.backend))
        return registry


def build_tool_registry(store: Any, single_cell_backend: Any | None = None) -> AgentToolRegistry:
    registry = AgentToolRegistry()
    PaperToolkit(store).register_tools(registry)
    SingleCellSequencingToolkit(single_cell_backend).register_tools(registry)
    return registry


def build_analyst_registry(store: Any) -> AgentToolRegistry:
    registry = AgentToolRegistry()
    PaperToolkit(store).register_tools(registry)
    return registry


def build_consultant_registry(store: Any, single_cell_backend: Any | None = None) -> AgentToolRegistry:
    registry = AgentToolRegistry()
    PaperToolkit(store).register_tools(registry)
    SingleCellSequencingToolkit(single_cell_backend).register_tools(registry)
    return registry
