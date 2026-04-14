from __future__ import annotations

from typing import Any, Callable, Dict, List


def build_tool_specs() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "name": "read_dataset_summary",
            "description": "Read the dataset summary and top-level task metadata.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "type": "function",
            "name": "read_label_distribution",
            "description": "Read the label distribution for a dataset annotation column such as cell_type or batch.",
            "parameters": {
                "type": "object",
                "properties": {"label_key": {"type": "string"}},
                "required": ["label_key"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "read_prior_resource_summary",
            "description": "Read the structured summary of available prior resources.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "type": "function",
            "name": "check_prior_coverage",
            "description": "Estimate how well a named prior resource covers the current dataset genes.",
            "parameters": {
                "type": "object",
                "properties": {"resource_name": {"type": "string"}},
                "required": ["resource_name"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "search_index",
            "description": "Semantic search over one RAG channel index.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "channel": {"type": "string", "enum": ["dataset", "prior_resources", "prior_methods", "benchmark"]},
                    "top_k": {"type": "integer", "minimum": 1, "maximum": 10},
                },
                "required": ["query", "channel"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "read_paper_summary",
            "description": "Read the structured summary of a retrieved paper.",
            "parameters": {
                "type": "object",
                "properties": {"paper_id": {"type": "string"}},
                "required": ["paper_id"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "fetch_paper_section",
            "description": "Fetch a specific paper section, returning top chunks when the section is long.",
            "parameters": {
                "type": "object",
                "properties": {
                    "paper_id": {"type": "string"},
                    "section_type": {"type": "string"},
                    "top_n_chunks": {"type": "integer", "minimum": 1, "maximum": 5},
                },
                "required": ["paper_id", "section_type"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "query_marker_database",
            "description": "Read known marker genes by tissue and species from the local marker database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tissue": {"type": "string"},
                    "species": {"type": "string"},
                },
                "required": ["tissue", "species"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "query_pathway_database",
            "description": "Look up pathway or GO entries associated with a gene symbol.",
            "parameters": {
                "type": "object",
                "properties": {
                    "database": {"type": "string", "enum": ["msigdb", "go"]},
                    "gene": {"type": "string"},
                },
                "required": ["database", "gene"],
                "additionalProperties": False,
            },
        },
    ]


def build_tool_executor(store: Any) -> Dict[str, Callable[..., Any]]:
    return {
        "read_dataset_summary": lambda: store.read_dataset_summary(),
        "read_label_distribution": lambda label_key: store.read_label_distribution(label_key),
        "read_prior_resource_summary": lambda: store.read_prior_resource_summary(),
        "check_prior_coverage": lambda resource_name: store.check_prior_coverage(resource_name),
        "search_index": lambda query, channel, top_k=5: store.search_index(query=query, channel=channel, top_k=top_k),
        "read_paper_summary": lambda paper_id: store.read_paper_summary(paper_id),
        "fetch_paper_section": lambda paper_id, section_type, top_n_chunks=3: store.fetch_paper_section(
            paper_id=paper_id,
            section_type=section_type,
            top_n_chunks=top_n_chunks,
        ),
        "query_marker_database": lambda tissue, species: store.query_marker_database(tissue=tissue, species=species),
        "query_pathway_database": lambda database, gene: store.query_pathway_database(database=database, gene=gene),
    }
