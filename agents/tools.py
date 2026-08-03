"""AgentTool classes with the new informative tool names.

Layout:
- Paper / RAG tools     (existing — unchanged API, kept intact)
- Reference management  (list / info / preload for static refs)
- API query tools       (Ensembl, JASPAR, CellxGene, ...)
- RNA compute tools     (15)
- ATAC compute tools    (12)
- Multimodal compute    (9)
- Registry builders     (per-agent-role composition)

Tool names use the new convention: <modality>_<task_category>, e.g.
`rna_batch_integration` (not `rna_integrate`), `atac_motif_enrichment`, etc.
Every compute tool's `run()` is a thin adapter that delegates to the
corresponding sub-backend method — all real logic lives in `backend/`.
"""

from __future__ import annotations


from pathlib import Path
from typing import Any, Dict, Optional

from agents.tool_base import AgentTool, AgentToolRegistry, MultiToolBase


def _normalize_pipeline_trial_inputs(
    *,
    backend: Any,
    pipeline_name: str,
    pipeline_config: Dict[str, Any],
    evaluation: Dict[str, Any],
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Compatibility helper for older composite pipeline tests.

    The current planner prefers granular DAG tools, but older tests still exercise
    this function to ensure method choices line up with generated embedding keys.
    """
    del pipeline_name  # retained for API compatibility
    normalized_config = dict(pipeline_config or {})
    normalized_eval = dict(evaluation or {})
    supported = backend.supported_capabilities() if hasattr(backend, "supported_capabilities") else {}
    rna_supported = supported.get("rna", {}) if isinstance(supported, dict) else {}

    for stage, capability in (
        ("normalize", "normalize"),
        ("features", "features"),
        ("feature_selection", "features"),
        ("embed", "embed"),
        ("cluster", "cluster"),
        ("annotate", "annotate"),
    ):
        key = f"{stage}.method"
        method = normalized_config.get(key)
        choices = ((rna_supported.get(capability) or {}).get("supported_methods") or [])
        if method is not None and choices and method not in choices:
            normalized_config[key] = choices[0]

    embed_method = normalized_config.get("embed.method")
    if embed_method:
        embedding_key = _dimensionality_output_key(str(embed_method)) or f"X_{embed_method}"
        normalized_eval["embedding_key"] = embedding_key
        normalized_config["cluster.embedding_key"] = embedding_key

    cluster_method = normalized_config.get("cluster.method")
    if cluster_method and not normalized_eval.get("cluster_key"):
        normalized_eval["cluster_key"] = str(cluster_method)
    if normalized_eval.get("cluster_key"):
        normalized_config["cluster.cluster_key"] = normalized_eval["cluster_key"]

    return normalized_config, normalized_eval


# =====================================================================
# Paper / RAG tools (existing — kept intact for backward compatibility)
# =====================================================================

class ReadDatasetSummary(AgentTool):
    name = "read_dataset_summary"
    description = "Read the dataset summary and top-level task metadata."
    parameters = {"type": "object", "properties": {}, "additionalProperties": False}

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        return self.backend.read_dataset_summary()


class ReadLabelDistribution(AgentTool):
    name = "read_label_distribution"
    description = "Read the label distribution for a dataset annotation column such as cell_type or batch."
    parameters = {
        "type": "object",
        "properties": {"label_key": {"type": "string"}},
        "required": ["label_key"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        return self.backend.read_label_distribution(kwargs["label_key"])


class ReadPriorResourceSummary(AgentTool):
    name = "read_prior_resource_summary"
    description = "Read the structured summary of available prior resources."
    parameters = {"type": "object", "properties": {}, "additionalProperties": False}

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        return self.backend.read_prior_resource_summary()


class CheckPriorCoverage(AgentTool):
    name = "check_prior_coverage"
    description = "Estimate how well a named prior resource covers the current dataset genes."
    parameters = {
        "type": "object",
        "properties": {"resource_name": {"type": "string"}},
        "required": ["resource_name"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        return self.backend.check_prior_coverage(kwargs["resource_name"])


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

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        return self.backend.search_index(
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

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        return self.backend.read_paper_summary(kwargs["paper_id"])


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

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        return self.backend.fetch_paper_section(
            paper_id=kwargs["paper_id"],
            section_type=kwargs["section_type"],
            top_n_chunks=kwargs.get("top_n_chunks", 3),
        )


class QueryMarkerDatabase(AgentTool):
    name = "query_marker_database"
    description = "Read known marker genes by tissue and species from the local marker database."
    parameters = {
        "type": "object",
        "properties": {"tissue": {"type": "string"}, "species": {"type": "string"}},
        "required": ["tissue", "species"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        return self.backend.query_marker_database(tissue=kwargs["tissue"], species=kwargs["species"])


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

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        return self.backend.query_pathway_database(database=kwargs["database"], gene=kwargs["gene"])


# =====================================================================
# Reference management (discovery / preload for static bulk refs)
# =====================================================================

_REF_CATEGORIES = [
    "genome", "annotation", "motifs", "atlas", "markers",
    "intervals", "pathways", "tf_targets", "ligand_receptor", "model",
]


class ListAvailableReferences(AgentTool):
    name = "list_available_references"
    description = "List static reference resources (genomes, motif DBs, atlases, etc.) available to compute tools, optionally filtered by category."
    parameters = {
        "type": "object",
        "properties": {"category": {"type": "string", "enum": _REF_CATEGORIES}},
        "additionalProperties": False,
    }

    def __init__(self, refs: Any):
        self.refs = refs

    def run(self, **kwargs: Any) -> Any:
        category = kwargs.get("category")
        return [m.to_dict() for m in self.refs.list_available(category=category)]


class GetReferenceInfo(AgentTool):
    name = "get_reference_info"
    description = "Get metadata about one static reference resource (version, size, on-disk/in-memory status, source URL)."
    parameters = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
        "additionalProperties": False,
    }

    def __init__(self, refs: Any):
        self.refs = refs

    def run(self, **kwargs: Any) -> Any:
        return self.refs.info(kwargs["name"]).to_dict()


class EnsureReferenceLoaded(AgentTool):
    name = "ensure_reference_loaded"
    description = "Force a static reference to be downloaded (if needed) and parsed into memory. Use before a long compute pipeline to warm caches."
    parameters = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
        "additionalProperties": False,
    }

    def __init__(self, refs: Any):
        self.refs = refs

    def run(self, **kwargs: Any) -> Any:
        self.refs.ensure_loaded(kwargs["name"])
        return {"status": "ok", "name": kwargs["name"]}


# =====================================================================
# API query tools (model-visible; parameters are semantic queries)
# =====================================================================

class FetchGeneInfo(AgentTool):
    name = "fetch_gene_info"
    description = "Look up gene metadata (location, aliases, description) from Ensembl by gene symbol."
    parameters = {
        "type": "object",
        "properties": {
            "gene_symbol": {"type": "string"},
            "species": {"type": "string", "default": "homo_sapiens"},
        },
        "required": ["gene_symbol"],
        "additionalProperties": False,
    }

    def __init__(self, api: Dict[str, Any]):
        self.api = api

    def run(self, **kwargs: Any) -> Any:
        return self.api["ensembl"].gene_info(kwargs["gene_symbol"], kwargs.get("species", "homo_sapiens"))


class FetchMotifPWM(AgentTool):
    name = "fetch_motif_pwm"
    description = "Fetch a single motif PWM from JASPAR by motif ID, or search for motifs by TF symbol."
    parameters = {
        "type": "object",
        "properties": {
            "motif_id": {"type": "string"},
            "tf_symbol": {"type": "string"},
            "species_tax_id": {"type": "string"},
        },
        "additionalProperties": False,
    }

    def __init__(self, api: Dict[str, Any]):
        self.api = api

    def run(self, **kwargs: Any) -> Any:
        if kwargs.get("motif_id"):
            return self.api["jaspar"].motif(kwargs["motif_id"])
        if kwargs.get("tf_symbol"):
            return self.api["jaspar"].search_by_tf(kwargs["tf_symbol"], kwargs.get("species_tax_id"))
        raise ValueError("Provide either motif_id or tf_symbol.")


class SearchReferenceAtlas(AgentTool):
    name = "search_reference_atlas"
    description = "Search CellxGene Discover for reference atlases by tissue / species / assay. Returns ranked candidates to pass into label transfer tools."
    parameters = {
        "type": "object",
        "properties": {
            "tissue": {"type": "string"},
            "species": {"type": "string"},
            "assay": {"type": "string"},
        },
        "additionalProperties": False,
    }

    def __init__(self, api: Dict[str, Any]):
        self.api = api

    def run(self, **kwargs: Any) -> Any:
        return self.api["cellxgene"].search_datasets(
            tissue=kwargs.get("tissue"),
            species=kwargs.get("species"),
            assay=kwargs.get("assay"),
        )


class FetchPathwayMembers(AgentTool):
    name = "fetch_pathway_members"
    description = "Fetch the gene members of a pathway from KEGG or Reactome by pathway ID."
    parameters = {
        "type": "object",
        "properties": {
            "pathway_id": {"type": "string"},
            "database": {"type": "string", "enum": ["kegg", "reactome"]},
        },
        "required": ["pathway_id", "database"],
        "additionalProperties": False,
    }

    def __init__(self, api: Dict[str, Any]):
        self.api = api

    def run(self, **kwargs: Any) -> Any:
        if kwargs["database"] == "kegg":
            return self.api["kegg"].pathway_members(kwargs["pathway_id"])
        return self.api["reactome"].pathway_members(kwargs["pathway_id"])


class FetchProteinInteractions(AgentTool):
    name = "fetch_protein_interactions"
    description = "Fetch protein-protein interactions from STRING around a gene."
    parameters = {
        "type": "object",
        "properties": {
            "gene_symbol": {"type": "string"},
            "species_tax_id": {"type": "string", "default": "9606"},
            "score_min": {"type": "number", "minimum": 0.0, "maximum": 1.0, "default": 0.7},
        },
        "required": ["gene_symbol"],
        "additionalProperties": False,
    }

    def __init__(self, api: Dict[str, Any]):
        self.api = api

    def run(self, **kwargs: Any) -> Any:
        return self.api["string"].interactions(
            kwargs["gene_symbol"],
            species_tax_id=kwargs.get("species_tax_id", "9606"),
            score_min=kwargs.get("score_min", 0.7),
        )


class FetchDiseaseAssociations(AgentTool):
    name = "fetch_disease_associations"
    description = "Fetch disease associations for a gene from Open Targets."
    parameters = {
        "type": "object",
        "properties": {"gene_symbol": {"type": "string"}},
        "required": ["gene_symbol"],
        "additionalProperties": False,
    }

    def __init__(self, api: Dict[str, Any]):
        self.api = api

    def run(self, **kwargs: Any) -> Any:
        return self.api["opentargets"].disease_associations(kwargs["gene_symbol"])


class FetchGOAnnotations(AgentTool):
    name = "fetch_go_annotations"
    description = "Fetch Gene Ontology annotations for a gene from QuickGO."
    parameters = {
        "type": "object",
        "properties": {
            "gene_symbol": {"type": "string"},
            "species_tax_id": {"type": "string", "default": "9606"},
            "ontology": {"type": "string", "enum": ["molecular_function", "biological_process", "cellular_component"]},
        },
        "required": ["gene_symbol", "ontology"],
        "additionalProperties": False,
    }

    def __init__(self, api: Dict[str, Any]):
        self.api = api

    def run(self, **kwargs: Any) -> Any:
        return self.api["quickgo"].annotations(
            kwargs["gene_symbol"],
            species_tax_id=kwargs.get("species_tax_id", "9606"),
            ontology=kwargs["ontology"],
        )


# =====================================================================
# Reusable schema fragments
# =====================================================================

_IO_PATHS = {
    "input_h5ad_path": {"type": "string"},
    "output_h5ad_path": {"type": "string"},
}
_IO_REQUIRED = ["input_h5ad_path", "output_h5ad_path"]
_TRAINING_DEVICE_OPTIONS = {
    "accelerator": {"type": "string", "enum": ["auto", "cpu", "cuda", "gpu", "mps"]},
    "devices": {
        "oneOf": [
            {"type": "string"},
            {"type": "integer", "minimum": 1},
        ]
    },
    "precision": {
        "oneOf": [
            {"type": "string"},
            {"type": "integer"},
        ]
    },
}


def _read_adata(path: str):
    import scanpy as sc
    return sc.read_h5ad(path)


def _write_adata(adata, path: str):
    from backend.artifacts import write_h5ad

    write_h5ad(adata, path, compression=True)


def _ok_result(path: str, method: str, adata, extra: Optional[dict] = None) -> dict:
    result = {
        "status": "ok",
        "output_h5ad_path": path,
        "method": method,
        "n_cells": int(adata.n_obs),
        "n_genes": int(adata.n_vars),
        "available_embeddings": sorted(list(adata.obsm.keys())),
    }
    if extra:
        result.update(extra)
    return result


def _has_key(container: Any, key: str) -> bool:
    try:
        return key in container
    except TypeError:
        return False


def _require_slot_key(adata: Any, slot: str, key: str, *, tool: str) -> None:
    container = getattr(adata, slot, None)
    if container is None or not _has_key(container, key):
        raise ValueError(f"{tool} completed but did not produce required adata.{slot}[{key!r}].")


def _require_uns_key(adata: Any, key: str, *, tool: str) -> None:
    _require_slot_key(adata, "uns", key, tool=tool)


def _require_obs_key(adata: Any, key: str, *, tool: str) -> None:
    _require_slot_key(adata, "obs", key, tool=tool)


def _require_var_key(adata: Any, key: str, *, tool: str) -> None:
    _require_slot_key(adata, "var", key, tool=tool)


def _require_obsm_key(adata: Any, key: str, *, tool: str) -> None:
    _require_slot_key(adata, "obsm", key, tool=tool)


def _require_result_keys(result: dict[str, Any], keys: tuple[str, ...], *, tool: str) -> None:
    missing = [key for key in keys if key not in result]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"{tool} completed but result is missing required key(s): {joined}.")


def _result_to_dict(result: Any, *, tool: str, required_keys: tuple[str, ...] = ()) -> dict[str, Any]:
    if not hasattr(result, "to_dict"):
        raise ValueError(f"{tool} completed but did not return a result object with to_dict().")
    payload = result.to_dict()
    if not isinstance(payload, dict):
        raise ValueError(f"{tool}.to_dict() returned {type(payload).__name__}, expected dict.")
    _require_result_keys(payload, required_keys, tool=tool)
    return payload


def _require_file(path: str | Path, *, tool: str) -> None:
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        raise ValueError(f"{tool} completed but did not write a non-empty output file at {path}.")


def _write_multimodal_result(result: Any, path: str | Path, *, tool: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(result, "write_h5mu"):
        result.write_h5mu(str(path))
    elif hasattr(result, "write_h5ad"):
        result.write_h5ad(str(path))
    else:
        raise ValueError(f"{tool} completed but returned no write_h5mu/write_h5ad-capable object.")
    _require_file(path, tool=tool)


def _qc_uns_key(method: str) -> Optional[str]:
    return {
        "basic": "qc",
        "scrublet": "qc_doublet",
    }.get(method)


def _annotation_output_key(method: str, obs_cluster: Optional[str]) -> str:
    if method == "celltypist" and not obs_cluster:
        return "celltype"
    if obs_cluster:
        return f"{obs_cluster}_celltype"
    return "celltype"


def _dimensionality_output_key(method: str) -> Optional[str]:
    return {
        "pca": "X_pca",
        "scvi": "X_scvi",
        "seurat_pca": "X_seurat_pca",
        "scanvi": "X_scanvi",
    }.get(method)


def _integration_output_key(method: str, embedding_key: str) -> Optional[str]:
    if method == "harmony":
        return "X_harmony" if embedding_key == "X_pca" else f"{embedding_key}_harmony"
    if method == "scvi":
        return "X_scvi_integrated"
    if method == "scanorama":
        return "X_scanorama"
    return None


def _projection_output_key(method: str) -> Optional[str]:
    return {
        "umap": "X_umap",
        "tsne": "X_tsne",
        "fa": "X_draw_graph_fa",
    }.get(method)


# =====================================================================
# RNA compute tools (15)
# =====================================================================

class RnaQualityControl(AgentTool):
    name = "rna_quality_control"
    description = (
        "Run scRNA-seq quality control on an AnnData file. Covers basic cell/gene filtering, "
        "doublet detection (Scrublet, scDblFinder), and ambient RNA removal (SoupX, CellBender, EmptyDrops)."
    )
    parameters = {
        "type": "object",
        "properties": {
            **_IO_PATHS,
            "method": {"type": "string", "enum": ["basic", "scrublet", "scdblfinder", "soupx", "cellbender", "emptydrops"]},
            "min_genes": {"type": "integer", "minimum": 0},
            "max_pct_mito": {"type": "number", "minimum": 0},
            "min_cells": {"type": "integer", "minimum": 0},
            "mt_pattern": {"type": "string"},
            "expected_doublet_rate": {"type": "number", "minimum": 0},
        },
        "required": [*_IO_REQUIRED, "method"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        adata = self.backend.rna.qc(
            adata,
            method=kwargs["method"],
            min_genes=kwargs.get("min_genes", 200),
            max_pct_mito=kwargs.get("max_pct_mito", 20.0),
            min_cells=kwargs.get("min_cells", 3),
            mt_pattern=kwargs.get("mt_pattern", "^MT-"),
            expected_doublet_rate=kwargs.get("expected_doublet_rate", 0.06),
        )
        qc_key = _qc_uns_key(kwargs["method"])
        if qc_key:
            _require_uns_key(adata, qc_key, tool=f"{self.name}({kwargs['method']})")
        _write_adata(adata, kwargs["output_h5ad_path"])
        return _ok_result(kwargs["output_h5ad_path"], kwargs["method"], adata)


class RnaNormalization(AgentTool):
    name = "rna_normalization"
    description = "Normalize an scRNA-seq AnnData file. log1p (standard), SCTransform or scran (via R)."
    parameters = {
        "type": "object",
        "properties": {
            **_IO_PATHS,
            "method": {"type": "string", "enum": ["log1p", "sctransform", "scran"]},
            "target_sum": {"type": "number", "exclusiveMinimum": 0},
        },
        "required": [*_IO_REQUIRED, "method"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        adata = self.backend.rna.normalize(
            adata, method=kwargs["method"], target_sum=kwargs.get("target_sum", 1e4)
        )
        _require_uns_key(adata, "normalization", tool=f"{self.name}({kwargs['method']})")
        _write_adata(adata, kwargs["output_h5ad_path"])
        return _ok_result(kwargs["output_h5ad_path"], kwargs["method"], adata)


class RnaFeatureSelection(AgentTool):
    name = "rna_feature_selection"
    description = "Select highly variable genes using Seurat v3, CellRanger, or scanpy-default flavor."
    parameters = {
        "type": "object",
        "properties": {
            **_IO_PATHS,
            "method": {"type": "string", "enum": ["seurat_v3", "cellranger", "scanpy_hvg"]},
            "n_top": {"type": "integer", "minimum": 1},
            "batch_key": {"type": "string"},
        },
        "required": [*_IO_REQUIRED, "method"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        adata = self.backend.rna.select_features(
            adata, method=kwargs["method"], n_top=kwargs.get("n_top", 2000), batch_key=kwargs.get("batch_key")
        )
        _require_var_key(adata, "highly_variable", tool=f"{self.name}({kwargs['method']})")
        _require_uns_key(adata, "feature_selection", tool=f"{self.name}({kwargs['method']})")
        _write_adata(adata, kwargs["output_h5ad_path"])
        return _ok_result(kwargs["output_h5ad_path"], kwargs["method"], adata)


class RnaDimensionalityReduction(AgentTool):
    name = "rna_dimensionality_reduction"
    description = (
        "Compute a latent embedding for an scRNA-seq AnnData file. "
        "PCA (fast baseline), scVI (deep generative, supports batch), Seurat PCA (via R), scANVI (semi-supervised, needs labels)."
    )
    parameters = {
        "type": "object",
        "properties": {
            **_IO_PATHS,
            "method": {"type": "string", "enum": ["pca", "scvi", "seurat_pca", "scanvi"]},
            "batch_key": {"type": "string"},
            "label_key": {"type": "string"},
            "n_latent": {"type": "integer", "minimum": 1},
            "n_layers": {"type": "integer", "minimum": 1},
            "n_epochs": {"type": "integer", "minimum": 1},
            "n_pcs": {"type": "integer", "minimum": 1},
            "random_seed": {"type": "integer"},
            **_TRAINING_DEVICE_OPTIONS,
        },
        "required": [*_IO_REQUIRED, "method"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        adata = self.backend.rna.embed(
            adata,
            method=kwargs["method"],
            batch_key=kwargs.get("batch_key"),
            label_key=kwargs.get("label_key"),
            n_latent=kwargs.get("n_latent", 30),
            n_layers=kwargs.get("n_layers", 2),
            n_epochs=kwargs.get("n_epochs"),
            n_pcs=kwargs.get("n_pcs", 50),
            random_seed=kwargs.get("random_seed", 42),
            accelerator=kwargs.get("accelerator", "auto"),
            devices=kwargs.get("devices", "auto"),
            precision=kwargs.get("precision"),
        )
        output_key = _dimensionality_output_key(kwargs["method"])
        if output_key:
            _require_obsm_key(adata, output_key, tool=f"{self.name}({kwargs['method']})")
        _write_adata(adata, kwargs["output_h5ad_path"])
        return _ok_result(kwargs["output_h5ad_path"], kwargs["method"], adata)


class RnaBatchIntegration(AgentTool):
    name = "rna_batch_integration"
    description = (
        "Remove batch effects in scRNA-seq using Harmony, LIGER, scVI, BBKNN, or Scanorama. "
        "Writes an integrated embedding into adata.obsm (e.g. X_harmony, X_scvi_integrated)."
    )
    parameters = {
        "type": "object",
        "properties": {
            **_IO_PATHS,
            "method": {"type": "string", "enum": ["harmony", "liger", "scvi", "bbknn", "scanorama"]},
            "batch_key": {"type": "string"},
            "embedding_key": {"type": "string"},
            "n_pcs": {"type": "integer", "minimum": 1},
            "n_latent": {"type": "integer", "minimum": 1},
            "theta": {"type": "number"},
            "n_epochs": {"type": "integer", "minimum": 1},
            **_TRAINING_DEVICE_OPTIONS,
        },
        "required": [*_IO_REQUIRED, "method", "batch_key"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        adata = self.backend.rna.integrate(
            adata,
            method=kwargs["method"],
            batch_key=kwargs["batch_key"],
            embedding_key=kwargs.get("embedding_key", "X_pca"),
            n_pcs=kwargs.get("n_pcs", 50),
            n_latent=kwargs.get("n_latent", 30),
            theta=kwargs.get("theta", 2.0),
            n_epochs=kwargs.get("n_epochs"),
            accelerator=kwargs.get("accelerator", "auto"),
            devices=kwargs.get("devices", "auto"),
            precision=kwargs.get("precision"),
        )
        embedding_key = kwargs.get("embedding_key", "X_pca")
        output_key = _integration_output_key(kwargs["method"], embedding_key)
        if output_key:
            _require_obsm_key(adata, output_key, tool=f"{self.name}({kwargs['method']})")
        elif kwargs["method"] == "bbknn":
            _require_uns_key(adata, "neighbors", tool=f"{self.name}({kwargs['method']})")
        _require_uns_key(adata, "batch_integration", tool=f"{self.name}({kwargs['method']})")
        _write_adata(adata, kwargs["output_h5ad_path"])
        return _ok_result(kwargs["output_h5ad_path"], kwargs["method"], adata)


class RnaClustering(AgentTool):
    name = "rna_clustering"
    description = (
        "Run Leiden/Louvain clustering on a precomputed embedding stored in adata.obsm. "
        "Optionally computes NMI/ARI against a reference label column."
    )
    parameters = {
        "type": "object",
        "properties": {
            **_IO_PATHS,
            "embedding_key": {"type": "string"},
            "method": {"type": "string", "enum": ["leiden", "louvain"]},
            "n_neighbors": {"type": "integer", "minimum": 1},
            "resolution": {"type": "number", "exclusiveMinimum": 0},
            "cluster_key": {"type": "string"},
            "label_key": {"type": "string"},
        },
        "required": [*_IO_REQUIRED, "embedding_key"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        adata = self.backend.rna.cluster(
            adata,
            embedding_key=kwargs["embedding_key"],
            method=kwargs.get("method", "leiden"),
            n_neighbors=kwargs.get("n_neighbors", 15),
            resolution=kwargs.get("resolution", 1.0),
            cluster_key=kwargs.get("cluster_key"),
            label_key=kwargs.get("label_key"),
        )
        cluster_key = kwargs.get("cluster_key") or f"{kwargs['embedding_key'].replace('X_', '')}_clusters"
        _require_obs_key(adata, cluster_key, tool=f"{self.name}({kwargs.get('method', 'leiden')})")
        if kwargs.get("label_key"):
            _require_uns_key(adata, f"{cluster_key}_metrics", tool=f"{self.name}({kwargs.get('method', 'leiden')})")
        _write_adata(adata, kwargs["output_h5ad_path"])
        return _ok_result(
            kwargs["output_h5ad_path"],
            kwargs.get("method", "leiden"),
            adata,
            extra={"cluster_key": cluster_key, "metrics": adata.uns.get(f"{cluster_key}_metrics", {})},
        )


class RnaCelltypeAnnotation(AgentTool):
    name = "rna_celltype_annotation"
    description = (
        "Annotate cluster labels with cell types. Methods: gpt4 (LLM marker interpretation), "
        "cellmarker (local DB lookup), celltypist (pretrained classifier), singler/azimuth (R-based), scarches (reference mapping)."
    )
    parameters = {
        "type": "object",
        "properties": {
            **_IO_PATHS,
            "method": {"type": "string", "enum": ["gpt4", "cellmarker", "celltypist", "singler", "azimuth", "scarches"]},
            "obs_cluster": {"type": "string"},
            "species": {"type": "string"},
            "tissue_type": {"type": "string"},
            "cancer_type": {"type": "string"},
            "model": {"type": "string"},
            "openai_api_key": {"type": "string"},
            "reference_atlas": {"type": "string"},
        },
        "required": [*_IO_REQUIRED, "method"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        adata = self.backend.rna.annotate(
            adata,
            method=kwargs["method"],
            obs_cluster=kwargs.get("obs_cluster"),
            species=kwargs.get("species", ""),
            tissue_type=kwargs.get("tissue_type", ""),
            cancer_type=kwargs.get("cancer_type", "Normal"),
            model=kwargs.get("model", "Immune_All_Low.pkl"),
            openai_api_key=kwargs.get("openai_api_key"),
            reference_atlas=kwargs.get("reference_atlas"),
        )
        annotation_key = _annotation_output_key(kwargs["method"], kwargs.get("obs_cluster"))
        _require_obs_key(adata, annotation_key, tool=f"{self.name}({kwargs['method']})")
        _require_uns_key(adata, "annotation", tool=f"{self.name}({kwargs['method']})")
        _write_adata(adata, kwargs["output_h5ad_path"])
        return _ok_result(
            kwargs["output_h5ad_path"],
            kwargs["method"],
            adata,
            extra={"annotation_key": annotation_key},
        )


class RnaDifferentialExpression(AgentTool):
    name = "rna_differential_expression"
    description = (
        "Compute differential expression grouped by an obs column. "
        "Methods: wilcoxon, t-test, logreg (scanpy); MAST, edgeR/DESeq2 pseudobulk (R)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "input_h5ad_path": {"type": "string"},
            "group_key": {"type": "string"},
            "method": {"type": "string", "enum": ["wilcoxon", "t", "logreg", "mast", "edger_pseudobulk", "deseq2_pseudobulk"]},
            "reference": {"type": "string"},
            "sample_key": {"type": "string"},
            "output_dir": {"type": "string"},
            "top_n": {"type": "integer", "minimum": 1},
        },
        "required": ["input_h5ad_path", "group_key", "method"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        result = self.backend.rna.differential_expression(
            adata,
            group_key=kwargs["group_key"],
            method=kwargs["method"],
            reference=kwargs.get("reference", "rest"),
            sample_key=kwargs.get("sample_key"),
            output_dir=Path(kwargs["output_dir"]) if kwargs.get("output_dir") else None,
            top_n=kwargs.get("top_n", 50),
        )
        return _result_to_dict(
            result,
            tool=f"{self.name}({kwargs['method']})",
            required_keys=("method", "group_key", "n_groups", "n_genes", "top_per_group"),
        )


class Rna2DProjection(AgentTool):
    name = "rna_2d_projection"
    description = "Compute a 2D layout for visualization. UMAP, t-SNE, or Force Atlas. Writes adata.obsm (X_umap / X_tsne / X_draw_graph_fa)."
    parameters = {
        "type": "object",
        "properties": {
            **_IO_PATHS,
            "embedding_key": {"type": "string"},
            "method": {"type": "string", "enum": ["umap", "tsne", "fa"]},
            "n_neighbors": {"type": "integer", "minimum": 1},
            "random_seed": {"type": "integer"},
        },
        "required": [*_IO_REQUIRED, "embedding_key", "method"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        adata = self.backend.rna.visualize(
            adata,
            method=kwargs["method"],
            embedding_key=kwargs["embedding_key"],
            n_neighbors=kwargs.get("n_neighbors", 15),
            random_seed=kwargs.get("random_seed", 42),
        )
        output_key = _projection_output_key(kwargs["method"])
        if output_key:
            _require_obsm_key(adata, output_key, tool=f"{self.name}({kwargs['method']})")
        _write_adata(adata, kwargs["output_h5ad_path"])
        return _ok_result(kwargs["output_h5ad_path"], kwargs["method"], adata)


# ---------- RNA Phase B+ tools (scaffold; backend bodies stubbed) ----------

class _StubComputeTool(AgentTool):
    """Base for compute tools whose backend body is NotImplementedError.

    The schema + tool wiring are complete; swap in a real implementation by
    filling in the matching backend module. The model will see a clear
    NotImplementedError if it tries to use one of these before you've wired
    it up, which is a correct failure mode (not a silent no-op).
    """

    def __init__(self, backend: Any):
        self.backend = backend

    def to_spec(self) -> Dict[str, Any]:
        spec = super().to_spec()
        description = str(spec.get("description") or "")
        if "not yet implemented" not in description.lower():
            spec["description"] = (
                "NOT YET IMPLEMENTED: this tool is scaffolded and will raise NotImplementedError "
                f"until its backend is implemented. {description}"
            )
        return spec


class RnaGeneProgramInference(_StubComputeTool):
    name = "rna_gene_program_inference"
    description = "Infer gene programs / modules: NMF, SCENIC, pagoda2, hotspot."
    parameters = {
        "type": "object",
        "properties": {
            **_IO_PATHS,
            "method": {"type": "string", "enum": ["nmf", "scenic", "pagoda2", "hotspot"]},
            "n_programs": {"type": "integer", "minimum": 1},
        },
        "required": [*_IO_REQUIRED, "method"],
        "additionalProperties": False,
    }

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        adata = self.backend.rna.gene_programs(adata, method=kwargs["method"], n_programs=kwargs.get("n_programs", 20))
        _write_adata(adata, kwargs["output_h5ad_path"])
        return _ok_result(kwargs["output_h5ad_path"], kwargs["method"], adata)


class RnaTrajectoryInference(_StubComputeTool):
    name = "rna_trajectory_inference"
    description = "Infer a cell-state trajectory using PAGA, Slingshot, Monocle3, or Palantir."
    parameters = {
        "type": "object",
        "properties": {
            **_IO_PATHS,
            "method": {"type": "string", "enum": ["paga", "slingshot", "monocle3", "palantir"]},
            "embedding_key": {"type": "string"},
        },
        "required": [*_IO_REQUIRED, "method"],
        "additionalProperties": False,
    }

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        adata = self.backend.rna.trajectory(adata, method=kwargs["method"])
        _write_adata(adata, kwargs["output_h5ad_path"])
        return _ok_result(kwargs["output_h5ad_path"], kwargs["method"], adata)


class RnaVelocity(_StubComputeTool):
    name = "rna_velocity"
    description = "Estimate RNA velocity: scvelo, velocyto, UnitVelo. Requires spliced/unspliced layers."
    parameters = {
        "type": "object",
        "properties": {
            **_IO_PATHS,
            "method": {"type": "string", "enum": ["scvelo", "velocyto", "unitvelo"]},
            "spliced_key": {"type": "string"},
            "unspliced_key": {"type": "string"},
        },
        "required": [*_IO_REQUIRED, "method"],
        "additionalProperties": False,
    }

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        adata = self.backend.rna.rna_velocity(
            adata,
            method=kwargs["method"],
            spliced_key=kwargs.get("spliced_key", "spliced"),
            unspliced_key=kwargs.get("unspliced_key", "unspliced"),
        )
        _write_adata(adata, kwargs["output_h5ad_path"])
        return _ok_result(kwargs["output_h5ad_path"], kwargs["method"], adata)


class RnaPerturbationAnalysis(_StubComputeTool):
    name = "rna_perturbation_analysis"
    description = "Perturbation-response analysis: Mixscape, GEARS, CPA."
    parameters = {
        "type": "object",
        "properties": {
            **_IO_PATHS,
            "method": {"type": "string", "enum": ["mixscape", "gears", "cpa"]},
            "perturbation_key": {"type": "string"},
        },
        "required": [*_IO_REQUIRED, "method", "perturbation_key"],
        "additionalProperties": False,
    }

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        adata = self.backend.rna.perturbation(adata, method=kwargs["method"], perturbation_key=kwargs["perturbation_key"])
        _write_adata(adata, kwargs["output_h5ad_path"])
        return _ok_result(kwargs["output_h5ad_path"], kwargs["method"], adata)


class RnaImputation(_StubComputeTool):
    name = "rna_imputation"
    description = "Impute / denoise the expression matrix: MAGIC, SAVER, ALRA, DCA."
    parameters = {
        "type": "object",
        "properties": {**_IO_PATHS, "method": {"type": "string", "enum": ["magic", "saver", "alra", "dca"]}},
        "required": [*_IO_REQUIRED, "method"],
        "additionalProperties": False,
    }

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        adata = self.backend.rna.impute(adata, method=kwargs["method"])
        _write_adata(adata, kwargs["output_h5ad_path"])
        return _ok_result(kwargs["output_h5ad_path"], kwargs["method"], adata)


class RnaCellCellCommunication(_StubComputeTool):
    name = "rna_cell_cell_communication"
    description = "Infer cell-cell communication: CellChat, CellPhoneDB, LIANA."
    parameters = {
        "type": "object",
        "properties": {
            "input_h5ad_path": {"type": "string"},
            "method": {"type": "string", "enum": ["cellchat", "cellphonedb", "liana"]},
            "group_key": {"type": "string"},
            "species": {"type": "string"},
        },
        "required": ["input_h5ad_path", "method", "group_key", "species"],
        "additionalProperties": False,
    }

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        result = self.backend.rna.cell_cell_comm(
            adata, method=kwargs["method"], group_key=kwargs["group_key"], species=kwargs["species"]
        )
        return _result_to_dict(result, tool=f"{self.name}({kwargs['method']})")


# =====================================================================
# ATAC compute tools (12)
# =====================================================================

class AtacQualityControl(AgentTool):
    name = "atac_quality_control"
    description = "scATAC-seq QC: basic filtering, TSS enrichment, fragment size, FRiP, blacklist overlap."
    parameters = {
        "type": "object",
        "properties": {
            **_IO_PATHS,
            "method": {"type": "string", "enum": ["basic", "tss_enrichment", "fragment_size", "frip"]},
            "build": {"type": "string", "enum": ["hg38", "mm10"]},
            "min_counts": {"type": "integer", "minimum": 0},
            "max_counts": {"type": "integer", "minimum": 0},
            "min_features": {"type": "integer", "minimum": 0},
            "min_cells": {"type": "integer", "minimum": 0},
            "fragments_path": {"type": "string"},
        },
        "required": [*_IO_REQUIRED, "method"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        adata = self.backend.atac.qc(
            adata,
            method=kwargs["method"],
            build=kwargs.get("build", "hg38"),
            min_counts=kwargs.get("min_counts", 1000),
            max_counts=kwargs.get("max_counts", 50_000),
            min_features=kwargs.get("min_features", 500),
            min_cells=kwargs.get("min_cells", 10),
            fragments_path=kwargs.get("fragments_path"),
        )
        if kwargs["method"] == "basic":
            _require_uns_key(adata, "qc", tool=f"{self.name}({kwargs['method']})")
        elif kwargs["method"] == "fragment_size":
            _require_uns_key(adata, "fragment_size", tool=f"{self.name}({kwargs['method']})")
        _write_adata(adata, kwargs["output_h5ad_path"])
        return _ok_result(kwargs["output_h5ad_path"], kwargs["method"], adata)


class AtacPeakCalling(AgentTool):
    name = "atac_peak_calling"
    description = "Call peaks from a fragments file: MACS2, MACS3, ArchR iterative merging, snapATAC2."
    parameters = {
        "type": "object",
        "properties": {
            "fragments_path": {"type": "string"},
            "output_peaks_path": {"type": "string"},
            "method": {"type": "string", "enum": ["macs2", "macs3", "archr_iter", "snapatac2"]},
            "genome_size": {"type": "string", "enum": ["hs", "mm"]},
            "q_value": {"type": "number", "exclusiveMinimum": 0},
        },
        "required": ["fragments_path", "output_peaks_path", "method"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        result = self.backend.atac.peak_calling(
            fragments_path=Path(kwargs["fragments_path"]),
            output_peaks_path=Path(kwargs["output_peaks_path"]),
            method=kwargs["method"],
            genome_size=kwargs.get("genome_size", "hs"),
            q_value=kwargs.get("q_value", 0.05),
        )
        payload = _result_to_dict(result, tool=f"{self.name}({kwargs['method']})")
        _require_file(kwargs["output_peaks_path"], tool=f"{self.name}({kwargs['method']})")
        return payload


class AtacFeatureMatrixConstruction(AgentTool):
    name = "atac_feature_matrix_construction"
    description = "Build the cell x feature matrix for scATAC: peaks, tiles, or bins."
    parameters = {
        "type": "object",
        "properties": {
            **_IO_PATHS,
            "method": {"type": "string", "enum": ["peaks", "tiles", "bins"]},
            "peakset": {"type": "string"},
            "tile_size": {"type": "integer", "minimum": 1},
            "fragments_path": {"type": "string"},
        },
        "required": [*_IO_REQUIRED, "method"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        adata = self.backend.atac.feature_matrix(
            adata,
            method=kwargs["method"],
            peakset=kwargs.get("peakset"),
            tile_size=kwargs.get("tile_size", 500),
            fragments_path=kwargs.get("fragments_path"),
        )
        _require_uns_key(adata, "feature_matrix", tool=f"{self.name}({kwargs['method']})")
        _write_adata(adata, kwargs["output_h5ad_path"])
        return _ok_result(kwargs["output_h5ad_path"], kwargs["method"], adata)


class AtacTfidfLsi(AgentTool):
    name = "atac_tfidf_lsi"
    description = "Apply TF-IDF normalization and LSI dimensionality reduction (or snapATAC2 Nystrom SVD) to scATAC data."
    parameters = {
        "type": "object",
        "properties": {
            **_IO_PATHS,
            "method": {"type": "string", "enum": ["tfidf_lsi_v1", "tfidf_lsi_v3", "snapatac2_svd"]},
            "n_components": {"type": "integer", "minimum": 1},
            "drop_first": {"type": "boolean"},
            "binarize": {"type": "boolean"},
            "random_seed": {"type": "integer"},
            "scale_factor": {"type": "number", "exclusiveMinimum": 0},
        },
        "required": [*_IO_REQUIRED],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        adata = self.backend.atac.tfidf_lsi(
            adata,
            method=kwargs.get("method", "tfidf_lsi_v3"),
            n_components=kwargs.get("n_components", 50),
            drop_first=kwargs.get("drop_first", True),
            binarize=kwargs.get("binarize", True),
            random_seed=kwargs.get("random_seed", 0),
            scale_factor=kwargs.get("scale_factor", 10_000.0),
        )
        _require_obsm_key(adata, "X_lsi", tool=f"{self.name}({kwargs.get('method', 'tfidf_lsi_v3')})")
        _require_uns_key(adata, "tfidf_lsi", tool=f"{self.name}({kwargs.get('method', 'tfidf_lsi_v3')})")
        _write_adata(adata, kwargs["output_h5ad_path"])
        return _ok_result(kwargs["output_h5ad_path"], kwargs.get("method", "tfidf_lsi_v3"), adata)


class AtacBatchIntegration(AgentTool):
    name = "atac_batch_integration"
    description = "Remove batch effects in scATAC: Harmony (on LSI), scVI-ATAC, LIGER-ATAC."
    parameters = {
        "type": "object",
        "properties": {
            **_IO_PATHS,
            "method": {"type": "string", "enum": ["harmony", "scvi_atac", "liger_atac"]},
            "batch_key": {"type": "string"},
            "embedding_key": {"type": "string"},
            "theta": {"type": "number"},
        },
        "required": [*_IO_REQUIRED, "method", "batch_key"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        adata = self.backend.atac.integrate(
            adata,
            method=kwargs["method"],
            batch_key=kwargs["batch_key"],
            embedding_key=kwargs.get("embedding_key", "X_lsi"),
            theta=kwargs.get("theta", 2.0),
        )
        if kwargs["method"] == "harmony":
            embedding_key = kwargs.get("embedding_key", "X_lsi")
            output_key = "X_harmony_lsi" if embedding_key == "X_lsi" else f"{embedding_key}_harmony"
            _require_obsm_key(adata, output_key, tool=f"{self.name}({kwargs['method']})")
        _require_uns_key(adata, "batch_integration", tool=f"{self.name}({kwargs['method']})")
        _write_adata(adata, kwargs["output_h5ad_path"])
        return _ok_result(kwargs["output_h5ad_path"], kwargs["method"], adata)


class AtacClustering(AgentTool):
    name = "atac_clustering"
    description = "Run Leiden/Louvain on an LSI (or integrated) embedding for scATAC."
    parameters = {
        "type": "object",
        "properties": {
            **_IO_PATHS,
            "embedding_key": {"type": "string"},
            "method": {"type": "string", "enum": ["leiden", "louvain"]},
            "resolution": {"type": "number"},
            "n_neighbors": {"type": "integer", "minimum": 1},
            "cluster_key": {"type": "string"},
        },
        "required": [*_IO_REQUIRED, "embedding_key"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        adata = self.backend.atac.cluster(
            adata,
            embedding_key=kwargs["embedding_key"],
            method=kwargs.get("method", "leiden"),
            resolution=kwargs.get("resolution", 1.0),
            n_neighbors=kwargs.get("n_neighbors", 15),
            cluster_key=kwargs.get("cluster_key"),
        )
        cluster_key = kwargs.get("cluster_key") or f"{kwargs['embedding_key'].replace('X_', '')}_clusters"
        _require_obs_key(adata, cluster_key, tool=f"{self.name}({kwargs.get('method', 'leiden')})")
        _write_adata(adata, kwargs["output_h5ad_path"])
        return _ok_result(
            kwargs["output_h5ad_path"],
            kwargs.get("method", "leiden"),
            adata,
            extra={"cluster_key": cluster_key},
        )


class AtacGeneActivityScore(_StubComputeTool):
    name = "atac_gene_activity_score"
    description = "Compute per-gene activity from ATAC peaks using Cicero, ArchR, or Signac. Requires a gene-annotation reference."
    parameters = {
        "type": "object",
        "properties": {
            **_IO_PATHS,
            "method": {"type": "string", "enum": ["cicero", "archr", "signac"]},
            "gene_annotation": {"type": "string", "enum": ["gencode_v44_human", "gencode_vM33_mouse"]},
        },
        "required": [*_IO_REQUIRED, "method", "gene_annotation"],
        "additionalProperties": False,
    }

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        adata = self.backend.atac.gene_activity(
            adata, method=kwargs["method"], gene_annotation=kwargs["gene_annotation"]
        )
        _write_adata(adata, kwargs["output_h5ad_path"])
        return _ok_result(kwargs["output_h5ad_path"], kwargs["method"], adata)


class AtacMotifEnrichment(_StubComputeTool):
    name = "atac_motif_enrichment"
    description = "Compute TF motif enrichment per cell/cluster using chromVAR or HOMER. Requires a motif DB and genome."
    parameters = {
        "type": "object",
        "properties": {
            **_IO_PATHS,
            "method": {"type": "string", "enum": ["chromvar", "homer"]},
            "motif_db": {"type": "string", "enum": ["jaspar2024_core_vertebrates", "cisbp_v2_human"]},
        },
        "required": [*_IO_REQUIRED, "method", "motif_db"],
        "additionalProperties": False,
    }

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        result = self.backend.atac.motif_enrichment(adata, motif_db=kwargs["motif_db"], method=kwargs["method"])
        return _result_to_dict(result, tool=f"{self.name}({kwargs['method']})")


class AtacDifferentialAccessibility(AgentTool):
    name = "atac_differential_accessibility"
    description = "Compute differentially accessible peaks by group: wilcoxon, logreg, edgeR/DESeq2 pseudobulk."
    parameters = {
        "type": "object",
        "properties": {
            "input_h5ad_path": {"type": "string"},
            "group_key": {"type": "string"},
            "method": {"type": "string", "enum": ["wilcoxon", "logreg", "edger_pseudobulk", "deseq2_pseudobulk"]},
            "output_dir": {"type": "string"},
            "top_n": {"type": "integer", "minimum": 1},
            "binarize": {"type": "boolean"},
        },
        "required": ["input_h5ad_path", "group_key", "method"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        result = self.backend.atac.differential_accessibility(
            adata,
            group_key=kwargs["group_key"],
            method=kwargs["method"],
            output_dir=kwargs.get("output_dir"),
            top_n=kwargs.get("top_n", 50),
            binarize=kwargs.get("binarize", True),
        )
        return _result_to_dict(
            result,
            tool=f"{self.name}({kwargs['method']})",
            required_keys=("method", "group_key", "n_groups", "n_genes", "top_per_group"),
        )


class AtacPeakToGeneLinking(AgentTool):
    name = "atac_peak_to_gene_linking"
    description = "Link peaks to candidate target genes: correlation-based peak2gene; Cicero/ArchR p2g are R-dependent."
    parameters = {
        "type": "object",
        "properties": {
            "input_h5ad_path": {"type": "string"},
            "method": {"type": "string", "enum": ["cicero", "peak2gene", "archr_p2g"]},
            "gene_annotation": {"type": "string", "enum": ["gencode_v44_human", "gencode_vM33_mouse"]},
            "max_distance": {"type": "integer", "minimum": 1},
            "gene_activity_key": {"type": "string"},
            "gene_names_key": {"type": "string"},
            "gene_coordinates_key": {"type": "string"},
            "min_correlation": {"type": "number"},
            "min_abs_correlation": {"type": "number", "minimum": 0},
            "allow_negative": {"type": "boolean"},
            "top_n_per_gene": {"type": "integer", "minimum": 1},
            "max_links_in_result": {"type": "integer", "minimum": 0},
            "output_links_path": {"type": "string"},
        },
        "required": ["input_h5ad_path", "method"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        result = self.backend.atac.peak_to_gene_linking(
            adata,
            method=kwargs["method"],
            gene_annotation=kwargs.get("gene_annotation", "gencode_v44_human"),
            max_distance=kwargs.get("max_distance", 500_000),
            gene_activity_key=kwargs.get("gene_activity_key", "gene_activity"),
            gene_names_key=kwargs.get("gene_names_key", "genes"),
            gene_coordinates_key=kwargs.get("gene_coordinates_key", "gene_coordinates"),
            min_correlation=kwargs.get("min_correlation", 0.0),
            min_abs_correlation=kwargs.get("min_abs_correlation"),
            allow_negative=kwargs.get("allow_negative", False),
            top_n_per_gene=kwargs.get("top_n_per_gene", 10),
            max_links_in_result=kwargs.get("max_links_in_result", 100),
            output_links_path=kwargs.get("output_links_path"),
        )
        return _result_to_dict(result, tool=f"{self.name}({kwargs['method']})", required_keys=("method", "n_links"))


class AtacTrajectoryInference(AgentTool):
    name = "atac_trajectory_inference"
    description = "Infer trajectories on scATAC data using PAGA or Slingshot on the LSI embedding."
    parameters = {
        "type": "object",
        "properties": {
            **_IO_PATHS,
            "embedding_key": {"type": "string"},
            "method": {"type": "string", "enum": ["paga", "slingshot"]},
            "group_key": {"type": "string"},
            "n_neighbors": {"type": "integer", "minimum": 1},
        },
        "required": [*_IO_REQUIRED, "method"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        adata = self.backend.atac.trajectory(
            adata,
            embedding_key=kwargs.get("embedding_key", "X_lsi"),
            method=kwargs["method"],
            group_key=kwargs.get("group_key"),
            n_neighbors=kwargs.get("n_neighbors", 15),
        )
        if kwargs["method"] == "paga":
            _require_uns_key(adata, "trajectory", tool=f"{self.name}({kwargs['method']})")
        _write_adata(adata, kwargs["output_h5ad_path"])
        return _ok_result(kwargs["output_h5ad_path"], kwargs["method"], adata)


class AtacCelltypeAnnotation(AgentTool):
    name = "atac_celltype_annotation"
    description = "Annotate scATAC cell types with marker peak matching; RNA label transfer remains R-dependent."
    parameters = {
        "type": "object",
        "properties": {
            **_IO_PATHS,
            "method": {"type": "string", "enum": ["rna_label_transfer", "marker_peaks"]},
            "reference_atlas": {"type": "string"},
            "group_key": {"type": "string"},
            "marker_peak_sets": {"type": "object"},
            "annotation_key": {"type": "string"},
            "min_markers": {"type": "integer", "minimum": 1},
        },
        "required": [*_IO_REQUIRED, "method"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        adata = self.backend.atac.annotate(
            adata,
            method=kwargs["method"],
            reference_atlas=kwargs.get("reference_atlas"),
            group_key=kwargs.get("group_key"),
            marker_peak_sets=kwargs.get("marker_peak_sets"),
            annotation_key=kwargs.get("annotation_key"),
            min_markers=kwargs.get("min_markers", 1),
        )
        if kwargs["method"] == "marker_peaks":
            output_key = kwargs.get("annotation_key") or f"{kwargs.get('group_key')}_celltype"
            _require_obs_key(adata, output_key, tool=f"{self.name}({kwargs['method']})")
            _require_uns_key(adata, "annotation", tool=f"{self.name}({kwargs['method']})")
        _write_adata(adata, kwargs["output_h5ad_path"])
        return _ok_result(kwargs["output_h5ad_path"], kwargs["method"], adata)


# =====================================================================
# Multimodal compute tools (9)
# =====================================================================

_DUAL_IO = {
    "rna_input_h5ad_path": {"type": "string"},
    "atac_input_h5ad_path": {"type": "string"},
    "output_h5ad_path": {"type": "string"},
}


class MultiPairedIntegration(_StubComputeTool):
    name = "multi_paired_integration"
    description = "Integrate paired RNA + ATAC from the same cells: WNN, MultiVI, Cobolt, scGLUE."
    parameters = {
        "type": "object",
        "properties": {
            **_DUAL_IO,
            "method": {"type": "string", "enum": ["wnn", "multivi", "cobolt", "scglue"]},
            "batch_key": {"type": "string"},
        },
        "required": ["rna_input_h5ad_path", "atac_input_h5ad_path", "output_h5ad_path", "method"],
        "additionalProperties": False,
    }

    def run(self, **kwargs: Any) -> Any:
        rna = _read_adata(kwargs["rna_input_h5ad_path"])
        atac = _read_adata(kwargs["atac_input_h5ad_path"])
        mdata = self.backend.multi.paired_integrate(rna, atac, method=kwargs["method"], batch_key=kwargs.get("batch_key"))
        _write_multimodal_result(mdata, kwargs["output_h5ad_path"], tool=f"{self.name}({kwargs['method']})")
        return {"status": "ok", "output_path": kwargs["output_h5ad_path"], "method": kwargs["method"]}


class MultiMosaicIntegration(_StubComputeTool):
    name = "multi_mosaic_integration"
    description = "Integrate heterogeneous modality combinations across datasets: Multigrate, StabMap, scMoMaT."
    parameters = {
        "type": "object",
        "properties": {
            "input_paths": {"type": "array", "items": {"type": "string"}, "minItems": 2},
            "modalities": {"type": "array", "items": {"type": "string", "enum": ["rna", "atac", "protein"]}, "minItems": 2},
            "output_path": {"type": "string"},
            "method": {"type": "string", "enum": ["multigrate", "stabmap", "scmomat"]},
        },
        "required": ["input_paths", "modalities", "output_path", "method"],
        "additionalProperties": False,
    }

    def run(self, **kwargs: Any) -> Any:
        adatas = [_read_adata(p) for p in kwargs["input_paths"]]
        result = self.backend.multi.mosaic_integrate(adatas, kwargs["modalities"], method=kwargs["method"])
        _write_multimodal_result(result, kwargs["output_path"], tool=f"{self.name}({kwargs['method']})")
        return {"status": "ok", "output_path": kwargs["output_path"], "method": kwargs["method"]}


class MultiUnpairedIntegration(_StubComputeTool):
    name = "multi_unpaired_integration"
    description = "Integrate unpaired RNA and ATAC: scGLUE, LIGER, Seurat CCA."
    parameters = {
        "type": "object",
        "properties": {
            **_DUAL_IO,
            "method": {"type": "string", "enum": ["scglue", "liger", "seurat_cca"]},
        },
        "required": ["rna_input_h5ad_path", "atac_input_h5ad_path", "output_h5ad_path", "method"],
        "additionalProperties": False,
    }

    def run(self, **kwargs: Any) -> Any:
        rna = _read_adata(kwargs["rna_input_h5ad_path"])
        atac = _read_adata(kwargs["atac_input_h5ad_path"])
        result = self.backend.multi.unpaired_integrate(rna, atac, method=kwargs["method"])
        _write_multimodal_result(result, kwargs["output_h5ad_path"], tool=f"{self.name}({kwargs['method']})")
        return {"status": "ok", "output_path": kwargs["output_h5ad_path"], "method": kwargs["method"]}


class MultiLabelTransfer(_StubComputeTool):
    name = "multi_label_transfer"
    description = "Transfer labels from a reference atlas to a query dataset: scANVI, Seurat CCA, scArches, CellTypist."
    parameters = {
        "type": "object",
        "properties": {
            **_IO_PATHS,
            "reference_atlas": {"type": "string"},
            "method": {"type": "string", "enum": ["scanvi", "seurat_cca", "scarches", "celltypist"]},
            "modality": {"type": "string", "enum": ["rna", "atac", "both"]},
        },
        "required": [*_IO_REQUIRED, "reference_atlas", "method"],
        "additionalProperties": False,
    }

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        adata = self.backend.multi.label_transfer(
            adata,
            reference_atlas=kwargs["reference_atlas"],
            method=kwargs["method"],
            modality=kwargs.get("modality", "rna"),
        )
        _write_adata(adata, kwargs["output_h5ad_path"])
        return _ok_result(kwargs["output_h5ad_path"], kwargs["method"], adata)


class MultiCrossModalityPrediction(_StubComputeTool):
    name = "multi_cross_modality_prediction"
    description = "Predict one modality from another: BABEL, Polarbear, scGLUE."
    parameters = {
        "type": "object",
        "properties": {
            **_IO_PATHS,
            "source_modality": {"type": "string", "enum": ["rna", "atac"]},
            "target_modality": {"type": "string", "enum": ["rna", "atac"]},
            "method": {"type": "string", "enum": ["babel", "polarbear", "scglue"]},
        },
        "required": [*_IO_REQUIRED, "source_modality", "target_modality", "method"],
        "additionalProperties": False,
    }

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        adata = self.backend.multi.cross_modality_predict(
            adata,
            source_modality=kwargs["source_modality"],
            target_modality=kwargs["target_modality"],
            method=kwargs["method"],
        )
        _write_adata(adata, kwargs["output_h5ad_path"])
        return _ok_result(kwargs["output_h5ad_path"], kwargs["method"], adata)


class MultiJointDifferentialExpression(_StubComputeTool):
    name = "multi_joint_differential_expression"
    description = "Joint DE across RNA and ATAC modalities: limma-voom, scanpy_joint, MAST joint."
    parameters = {
        "type": "object",
        "properties": {
            "rna_input_h5ad_path": {"type": "string"},
            "atac_input_h5ad_path": {"type": "string"},
            "group_key": {"type": "string"},
            "method": {"type": "string", "enum": ["limma_voom", "scanpy_joint", "mast_joint"]},
        },
        "required": ["rna_input_h5ad_path", "atac_input_h5ad_path", "group_key", "method"],
        "additionalProperties": False,
    }

    def run(self, **kwargs: Any) -> Any:
        rna = _read_adata(kwargs["rna_input_h5ad_path"])
        atac = _read_adata(kwargs["atac_input_h5ad_path"])
        result = self.backend.multi.joint_de(rna, atac, group_key=kwargs["group_key"], method=kwargs["method"])
        return _result_to_dict(result, tool=f"{self.name}({kwargs['method']})")


class MultiJointRnaVelocity(_StubComputeTool):
    name = "multi_joint_rna_velocity"
    description = "Joint RNA velocity using chromatin priors: MultiVelo, UnitVelo-multi."
    parameters = {
        "type": "object",
        "properties": {
            "rna_input_h5ad_path": {"type": "string"},
            "atac_input_h5ad_path": {"type": "string"},
            "output_h5ad_path": {"type": "string"},
            "method": {"type": "string", "enum": ["multivelo", "unitvelo_multi"]},
        },
        "required": ["rna_input_h5ad_path", "atac_input_h5ad_path", "output_h5ad_path", "method"],
        "additionalProperties": False,
    }

    def run(self, **kwargs: Any) -> Any:
        rna = _read_adata(kwargs["rna_input_h5ad_path"])
        atac = _read_adata(kwargs["atac_input_h5ad_path"])
        result = self.backend.multi.joint_rna_velocity(rna, atac, method=kwargs["method"])
        _write_multimodal_result(result, kwargs["output_h5ad_path"], tool=f"{self.name}({kwargs['method']})")
        return {"status": "ok", "output_path": kwargs["output_h5ad_path"], "method": kwargs["method"]}


class MultiGrnInference(_StubComputeTool):
    name = "multi_grn_inference"
    description = "Infer a gene regulatory network from paired RNA + ATAC: SCENIC+, FIGR, CellOracle."
    parameters = {
        "type": "object",
        "properties": {
            "rna_input_h5ad_path": {"type": "string"},
            "atac_input_h5ad_path": {"type": "string"},
            "output_edges_path": {"type": "string"},
            "method": {"type": "string", "enum": ["scenic_plus", "figr", "celloracle"]},
            "gene_annotation": {"type": "string", "enum": ["gencode_v44_human", "gencode_vM33_mouse"]},
        },
        "required": ["rna_input_h5ad_path", "atac_input_h5ad_path", "output_edges_path", "method"],
        "additionalProperties": False,
    }

    def run(self, **kwargs: Any) -> Any:
        rna = _read_adata(kwargs["rna_input_h5ad_path"])
        atac = _read_adata(kwargs["atac_input_h5ad_path"])
        result = self.backend.multi.grn_inference(
            rna, atac,
            method=kwargs["method"],
            gene_annotation=kwargs.get("gene_annotation", "gencode_v44_human"),
            output_edges_path=Path(kwargs["output_edges_path"]),
        )
        payload = _result_to_dict(result, tool=f"{self.name}({kwargs['method']})")
        _require_file(kwargs["output_edges_path"], tool=f"{self.name}({kwargs['method']})")
        return payload


class MultiFoundationModels(_StubComputeTool):
    name = "multi_foundation_models"
    description = "Run a pretrained single-cell foundation model (Geneformer, scGPT, scFoundation) for embedding, cell-type prediction, or perturbation response."
    parameters = {
        "type": "object",
        "properties": {
            **_IO_PATHS,
            "model": {"type": "string", "enum": ["geneformer", "scgpt", "scfoundation"]},
            "task": {"type": "string", "enum": ["embed", "predict_celltype", "perturbation_response"]},
        },
        "required": [*_IO_REQUIRED, "model", "task"],
        "additionalProperties": False,
    }

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        adata = self.backend.multi.foundation_model(adata, model=kwargs["model"], task=kwargs["task"])
        _write_adata(adata, kwargs["output_h5ad_path"])
        return _ok_result(kwargs["output_h5ad_path"], kwargs["model"], adata)


# =====================================================================
# Composite / pipeline tools (chain multiple backend methods in one call)
#
# These coexist with the granular tools above. Use a composite tool when
# the standard happy-path workflow is appropriate; drop to the granular
# tools when you need fine control over intermediate parameters or want
# to inspect outputs between steps.
# =====================================================================


class RnaPreprocess(AgentTool):
    name = "rna_preprocess"
    description = (
        "End-to-end scRNA-seq preprocessing: quality control -> normalization -> "
        "highly variable gene selection -> latent embedding. "
        "Use this for the STANDARD HAPPY-PATH workflow with default parameters. "
        "If you need fine control over intermediate thresholds, want to try multiple "
        "normalization methods, or want to inspect outputs between steps, use the "
        "individual tools (rna_quality_control, rna_normalization, rna_feature_selection, "
        "rna_dimensionality_reduction) instead."
    )
    parameters = {
        "type": "object",
        "properties": {
            "input_h5ad_path": {"type": "string"},
            "output_h5ad_path": {"type": "string"},
            # QC
            "min_genes": {"type": "integer", "minimum": 0},
            "max_pct_mito": {"type": "number", "minimum": 0},
            "min_cells": {"type": "integer", "minimum": 0},
            # Normalization
            "normalize_method": {"type": "string", "enum": ["log1p", "sctransform", "scran"]},
            "target_sum": {"type": "number", "exclusiveMinimum": 0},
            # Features
            "feature_method": {"type": "string", "enum": ["seurat_v3", "cellranger", "scanpy_hvg"]},
            "n_top_genes": {"type": "integer", "minimum": 1},
            "batch_key": {"type": "string"},
            # Embedding
            "embed_method": {"type": "string", "enum": ["pca", "scvi", "seurat_pca", "scanvi"]},
            "n_latent": {"type": "integer", "minimum": 1},
            "n_epochs": {"type": "integer", "minimum": 1},
            "random_seed": {"type": "integer"},
            **_TRAINING_DEVICE_OPTIONS,
        },
        "required": ["input_h5ad_path", "output_h5ad_path", "embed_method"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])
        n_cells_start = int(adata.n_obs)

        adata = self.backend.rna.qc(
            adata, method="basic",
            min_genes=kwargs.get("min_genes", 200),
            max_pct_mito=kwargs.get("max_pct_mito", 20.0),
            min_cells=kwargs.get("min_cells", 3),
        )
        _require_uns_key(adata, "qc", tool=f"{self.name}(qc)")
        n_cells_after_qc = int(adata.n_obs)

        adata = self.backend.rna.normalize(
            adata, method=kwargs.get("normalize_method", "log1p"),
            target_sum=kwargs.get("target_sum", 1e4),
        )
        _require_uns_key(adata, "normalization", tool=f"{self.name}({kwargs.get('normalize_method', 'log1p')})")

        adata = self.backend.rna.select_features(
            adata, method=kwargs.get("feature_method", "seurat_v3"),
            n_top=kwargs.get("n_top_genes", 2000),
            batch_key=kwargs.get("batch_key"),
        )
        _require_var_key(adata, "highly_variable", tool=f"{self.name}({kwargs.get('feature_method', 'seurat_v3')})")
        _require_uns_key(adata, "feature_selection", tool=f"{self.name}({kwargs.get('feature_method', 'seurat_v3')})")

        adata = self.backend.rna.embed(
            adata, method=kwargs["embed_method"],
            batch_key=kwargs.get("batch_key"),
            n_latent=kwargs.get("n_latent", 30),
            n_epochs=kwargs.get("n_epochs"),
            random_seed=kwargs.get("random_seed", 42),
            accelerator=kwargs.get("accelerator", "auto"),
            devices=kwargs.get("devices", "auto"),
            precision=kwargs.get("precision"),
        )
        output_key = _dimensionality_output_key(kwargs["embed_method"])
        if output_key:
            _require_obsm_key(adata, output_key, tool=f"{self.name}({kwargs['embed_method']})")

        _write_adata(adata, kwargs["output_h5ad_path"])
        return {
            "status": "ok",
            "output_h5ad_path": kwargs["output_h5ad_path"],
            "steps_run": ["qc", "normalize", "select_features", "embed"],
            "n_cells_start": n_cells_start,
            "n_cells_after_qc": n_cells_after_qc,
            "n_cells_removed": n_cells_start - n_cells_after_qc,
            "n_genes": int(adata.n_vars),
            "available_embeddings": sorted(list(adata.obsm.keys())),
            "embed_method": kwargs["embed_method"],
        }


class RnaClusterAndAnnotate(AgentTool):
    name = "rna_cluster_and_annotate"
    description = (
        "End-to-end scRNA-seq downstream analysis: clustering on a precomputed embedding -> "
        "differential expression per cluster -> cell type annotation. "
        "Use this after rna_preprocess for the STANDARD HAPPY-PATH downstream workflow. "
        "If you want to try multiple clustering resolutions or compare annotation methods, "
        "use the individual tools (rna_clustering, rna_differential_expression, "
        "rna_celltype_annotation) instead."
    )
    parameters = {
        "type": "object",
        "properties": {
            "input_h5ad_path": {"type": "string"},
            "output_h5ad_path": {"type": "string"},
            "embedding_key": {"type": "string"},
            # Cluster
            "resolution": {"type": "number", "exclusiveMinimum": 0},
            "n_neighbors": {"type": "integer", "minimum": 1},
            "label_key": {"type": "string"},
            # DE
            "de_method": {"type": "string", "enum": ["wilcoxon", "t", "logreg"]},
            # Annotation
            "annotate_method": {"type": "string", "enum": ["gpt4", "cellmarker", "celltypist"]},
            "species": {"type": "string"},
            "tissue_type": {"type": "string"},
            "cancer_type": {"type": "string"},
            "model": {"type": "string"},
            "openai_api_key": {"type": "string"},
        },
        "required": ["input_h5ad_path", "output_h5ad_path", "embedding_key", "annotate_method"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])

        adata = self.backend.rna.cluster(
            adata,
            embedding_key=kwargs["embedding_key"],
            resolution=kwargs.get("resolution", 1.0),
            n_neighbors=kwargs.get("n_neighbors", 15),
            label_key=kwargs.get("label_key"),
        )
        cluster_key = f"{kwargs['embedding_key'].replace('X_', '')}_clusters"
        _require_obs_key(adata, cluster_key, tool=self.name)
        if kwargs.get("label_key"):
            _require_uns_key(adata, f"{cluster_key}_metrics", tool=self.name)

        de_result = self.backend.rna.differential_expression(
            adata,
            group_key=cluster_key,
            method=kwargs.get("de_method", "wilcoxon"),
        )

        adata = self.backend.rna.annotate(
            adata,
            method=kwargs["annotate_method"],
            obs_cluster=cluster_key,
            species=kwargs.get("species", ""),
            tissue_type=kwargs.get("tissue_type", ""),
            cancer_type=kwargs.get("cancer_type", "Normal"),
            model=kwargs.get("model", "Immune_All_Low.pkl"),
            openai_api_key=kwargs.get("openai_api_key"),
        )
        annotation_key = _annotation_output_key(kwargs["annotate_method"], cluster_key)
        _require_obs_key(adata, annotation_key, tool=f"{self.name}({kwargs['annotate_method']})")
        _require_uns_key(adata, "annotation", tool=f"{self.name}({kwargs['annotate_method']})")

        _write_adata(adata, kwargs["output_h5ad_path"])
        return {
            "status": "ok",
            "output_h5ad_path": kwargs["output_h5ad_path"],
            "steps_run": ["cluster", "differential_expression", "annotate"],
            "cluster_key": cluster_key,
            "n_clusters": int(adata.obs[cluster_key].nunique()),
            "cluster_metrics": adata.uns.get(f"{cluster_key}_metrics", {}),
            "de_summary": {"method": de_result.method, "n_groups": de_result.n_groups},
            "annotate_method": kwargs["annotate_method"],
            "annotation_key": annotation_key,
        }


class AtacPreprocess(AgentTool):
    name = "atac_preprocess"
    description = (
        "End-to-end scATAC-seq preprocessing: quality control -> feature matrix construction -> "
        "TF-IDF normalization + LSI dimensionality reduction. "
        "Use this for the STANDARD HAPPY-PATH ATAC workflow. "
        "Assumes peak calling has already been run (use atac_peak_calling first if you have raw fragments). "
        "If you want fine control over parameters, use the individual tools (atac_quality_control, "
        "atac_feature_matrix_construction, atac_tfidf_lsi) instead."
    )
    parameters = {
        "type": "object",
        "properties": {
            "input_h5ad_path": {"type": "string"},
            "output_h5ad_path": {"type": "string"},
            "build": {"type": "string", "enum": ["hg38", "mm10"]},
            "feature_method": {"type": "string", "enum": ["peaks", "tiles", "bins"]},
            "peakset": {"type": "string"},
            "tile_size": {"type": "integer", "minimum": 1},
            "fragments_path": {"type": "string"},
            "lsi_method": {"type": "string", "enum": ["tfidf_lsi_v1", "tfidf_lsi_v3", "snapatac2_svd"]},
            "n_components": {"type": "integer", "minimum": 1},
            "binarize": {"type": "boolean"},
            "random_seed": {"type": "integer"},
            "scale_factor": {"type": "number", "exclusiveMinimum": 0},
        },
        "required": ["input_h5ad_path", "output_h5ad_path"],
        "additionalProperties": False,
    }

    def __init__(self, backend: Any):
        self.backend = backend

    def run(self, **kwargs: Any) -> Any:
        adata = _read_adata(kwargs["input_h5ad_path"])

        adata = self.backend.atac.qc(adata, method="basic", build=kwargs.get("build", "hg38"))
        _require_uns_key(adata, "qc", tool=f"{self.name}(qc)")
        adata = self.backend.atac.feature_matrix(
            adata,
            method=kwargs.get("feature_method", "peaks"),
            peakset=kwargs.get("peakset"),
            tile_size=kwargs.get("tile_size", 500),
            fragments_path=kwargs.get("fragments_path"),
        )
        _require_uns_key(adata, "feature_matrix", tool=f"{self.name}(feature_matrix)")
        adata = self.backend.atac.tfidf_lsi(
            adata,
            method=kwargs.get("lsi_method", "tfidf_lsi_v3"),
            n_components=kwargs.get("n_components", 50),
            binarize=kwargs.get("binarize", True),
            random_seed=kwargs.get("random_seed", 0),
            scale_factor=kwargs.get("scale_factor", 10_000.0),
        )
        _require_obsm_key(adata, "X_lsi", tool=f"{self.name}(tfidf_lsi)")
        _require_uns_key(adata, "tfidf_lsi", tool=f"{self.name}(tfidf_lsi)")

        _write_adata(adata, kwargs["output_h5ad_path"])
        return {
            "status": "ok",
            "output_h5ad_path": kwargs["output_h5ad_path"],
            "steps_run": ["qc", "feature_matrix", "tfidf_lsi"],
            "n_cells": int(adata.n_obs),
            "n_features": int(adata.n_vars),
            "available_embeddings": sorted(list(adata.obsm.keys())),
        }




# =====================================================================
# Toolkits
# =====================================================================

class PaperToolkit(MultiToolBase):
    """Literature-backed evidence retrieval."""

    toolkit_name = "paper"
    brief_description = "Tools for literature-backed evidence retrieval."

    def __init__(self, backend: Any):
        self.backend = backend

    def register_tools(self, registry: AgentToolRegistry) -> AgentToolRegistry:
        return (
            registry
            .register(SearchIndex(self.backend))
            .register(ReadPaperSummary(self.backend))
            .register(FetchPaperSection(self.backend))
        )


class DataInspectionToolkit(MultiToolBase):
    """Dataset and prior inspection tools backed by the single-cell backend."""

    toolkit_name = "data_inspection"
    brief_description = "Read dataset summaries, prior coverage, markers, and pathway matches."

    def __init__(self, backend: Any):
        self.backend = backend

    def register_tools(self, registry: AgentToolRegistry) -> AgentToolRegistry:
        return (
            registry
            .register(ReadDatasetSummary(self.backend))
            .register(ReadLabelDistribution(self.backend))
            .register(ReadPriorResourceSummary(self.backend))
            .register(CheckPriorCoverage(self.backend))
            .register(QueryMarkerDatabase(self.backend))
            .register(QueryPathwayDatabase(self.backend))
        )


class ReferenceManagementToolkit(MultiToolBase):
    """Discover, inspect, and preload static reference resources."""

    toolkit_name = "reference_management"
    brief_description = "List, inspect, and preload genomes, motif DBs, atlases, and other static references."

    def __init__(self, refs: Any):
        self.refs = refs

    def register_tools(self, registry: AgentToolRegistry) -> AgentToolRegistry:
        return (
            registry
            .register(ListAvailableReferences(self.refs))
            .register(GetReferenceInfo(self.refs))
            .register(EnsureReferenceLoaded(self.refs))
        )


class ApiQueryToolkit(MultiToolBase):
    """Parameterized REST-API lookups (Ensembl, JASPAR, CellxGene, Reactome, STRING, ...)."""

    toolkit_name = "api_query"
    brief_description = "Targeted lookups against external bioinformatics APIs."

    def __init__(self, api: Dict[str, Any]):
        self.api = api

    def register_tools(self, registry: AgentToolRegistry) -> AgentToolRegistry:
        return (
            registry
            .register(FetchGeneInfo(self.api))
            .register(FetchMotifPWM(self.api))
            .register(SearchReferenceAtlas(self.api))
            .register(FetchPathwayMembers(self.api))
            .register(FetchProteinInteractions(self.api))
            .register(FetchDiseaseAssociations(self.api))
            .register(FetchGOAnnotations(self.api))
        )


class RnaComputeToolkit(MultiToolBase):
    """15 RNA compute tools."""

    toolkit_name = "rna_compute"
    brief_description = "scRNA-seq compute methods (QC, normalization, DR, clustering, annotation, DE, ...)."

    def __init__(self, backend: Any):
        self.backend = backend

    def register_tools(self, registry: AgentToolRegistry) -> AgentToolRegistry:
        for cls in (
            # Granular (one tool per task category)
            RnaQualityControl,
            RnaNormalization,
            RnaFeatureSelection,
            RnaDimensionalityReduction,
            RnaBatchIntegration,
            RnaClustering,
            RnaCelltypeAnnotation,
            RnaDifferentialExpression,
            Rna2DProjection,
            RnaGeneProgramInference,
            RnaTrajectoryInference,
            RnaVelocity,
            RnaPerturbationAnalysis,
            RnaImputation,
            RnaCellCellCommunication,
            # Composite pipelines (happy-path shortcuts; coexist with granular)
            RnaPreprocess,
            RnaClusterAndAnnotate,
        ):
            registry.register(cls(self.backend))
        return registry


class AtacComputeToolkit(MultiToolBase):
    """12 ATAC compute tools."""

    toolkit_name = "atac_compute"
    brief_description = "scATAC-seq compute methods (QC, peak calling, LSI, motif enrichment, ...)."

    def __init__(self, backend: Any):
        self.backend = backend

    def register_tools(self, registry: AgentToolRegistry) -> AgentToolRegistry:
        for cls in (
            # Granular
            AtacQualityControl,
            AtacPeakCalling,
            AtacFeatureMatrixConstruction,
            AtacTfidfLsi,
            AtacBatchIntegration,
            AtacClustering,
            AtacGeneActivityScore,
            AtacMotifEnrichment,
            AtacDifferentialAccessibility,
            AtacPeakToGeneLinking,
            AtacTrajectoryInference,
            AtacCelltypeAnnotation,
            # Composite
            AtacPreprocess,
        ):
            registry.register(cls(self.backend))
        return registry


class MultimodalComputeToolkit(MultiToolBase):
    """9 multimodal compute tools."""

    toolkit_name = "multimodal_compute"
    brief_description = "Joint RNA + ATAC methods (paired/unpaired/mosaic integration, label transfer, GRN, foundation models)."

    def __init__(self, backend: Any):
        self.backend = backend

    def register_tools(self, registry: AgentToolRegistry) -> AgentToolRegistry:
        for cls in (
            MultiPairedIntegration,
            MultiMosaicIntegration,
            MultiUnpairedIntegration,
            MultiLabelTransfer,
            MultiCrossModalityPrediction,
            MultiJointDifferentialExpression,
            MultiJointRnaVelocity,
            MultiGrnInference,
            MultiFoundationModels,
        ):
            registry.register(cls(self.backend))
        return registry



# =====================================================================
# Per-agent registry builders
# =====================================================================

def build_analyst_registry(paper_backend: Any, backend: Any | None = None) -> AgentToolRegistry:
    """Analyst: paper / RAG plus lightweight dataset inspection. No compute, no refs, no API."""
    registry = AgentToolRegistry()
    if backend is not None:
        DataInspectionToolkit(backend).register_tools(registry)
    PaperToolkit(paper_backend).register_tools(registry)
    return registry


def build_consultant_registry(paper_backend: Any, backend: Any | None = None) -> AgentToolRegistry:
    """Consultant (planning): paper + reference management + API queries + compute tools."""
    registry = AgentToolRegistry()
    PaperToolkit(paper_backend).register_tools(registry)
    if backend is not None:
        DataInspectionToolkit(backend).register_tools(registry)
        ReferenceManagementToolkit(backend.refs).register_tools(registry)
        ApiQueryToolkit(backend.api).register_tools(registry)
        RnaComputeToolkit(backend).register_tools(registry)
        AtacComputeToolkit(backend).register_tools(registry)
        MultimodalComputeToolkit(backend).register_tools(registry)
    return registry


def _build_dag_tool_registry(backend: Any) -> AgentToolRegistry:
    registry = AgentToolRegistry()
    DataInspectionToolkit(backend).register_tools(registry)
    ReferenceManagementToolkit(backend.refs).register_tools(registry)
    ApiQueryToolkit(backend.api).register_tools(registry)
    RnaComputeToolkit(backend).register_tools(registry)
    AtacComputeToolkit(backend).register_tools(registry)
    MultimodalComputeToolkit(backend).register_tools(registry)
    return registry


def build_tool_consultant_registry(backend: Any) -> AgentToolRegistry:
    """ToolConsultant: DAG executable tools plus lightweight dataset inspection."""
    return _build_dag_tool_registry(backend)


def build_tool_executor_registry(backend: Any) -> AgentToolRegistry:
    """DAG executor tools: refs + API + compute + data inspection tools."""
    return _build_dag_tool_registry(backend)


def build_executor_registry(backend: Any) -> AgentToolRegistry:
    """Pure executor: refs + API + all compute tools. No paper tools."""
    registry = AgentToolRegistry()
    ReferenceManagementToolkit(backend.refs).register_tools(registry)
    ApiQueryToolkit(backend.api).register_tools(registry)
    RnaComputeToolkit(backend).register_tools(registry)
    AtacComputeToolkit(backend).register_tools(registry)
    MultimodalComputeToolkit(backend).register_tools(registry)
    return registry


def build_tool_registry(paper_backend: Any, backend: Any | None = None) -> AgentToolRegistry:
    """Union of everything — default for agents that want the maximal surface."""
    return build_consultant_registry(paper_backend, backend)
