"""Wiki graph traversal tools for the ToolConsultant agent.

Exposes tools the consultant calls during planning:
  - wiki_query_tasks    : entry point — list tasks filtered by modality
  - wiki_graph_query    : fetch a node's content + neighbors (lazy traversal)
  - wiki_fetch_resource : download a named resource and return resolved file paths
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.tool_base import AgentTool, AgentToolRegistry
from wiki.index import get_index, graph_query, query_tasks


class WikiQueryTasks(AgentTool):
    """List all task nodes, optionally filtered by modality."""

    name = "wiki_query_tasks"
    description = (
        "List all available analysis task nodes from the wiki knowledge graph. "
        "Returns task IDs, labels, modalities, and canonical pipeline stage order. "
        "Use this as the entry point to identify which task matches the user's request. "
        "Filter by modality when known ('rna', 'atac', or 'multi')."
    )
    parameters = {
        "type": "object",
        "properties": {
            "modality": {
                "type": "string",
                "enum": ["rna", "atac", "multi"],
                "description": "Filter tasks by modality. Omit to list all tasks.",
            }
        },
        "additionalProperties": False,
    }

    def run(self, *, modality: str | None = None, **_: Any) -> list[dict[str, Any]]:
        results = query_tasks(modality=modality)
        # canonical_pipeline removed from frontmatter; stages now come from includes edges.
        # Strip it from results so the consultant doesn't see a stale empty list.
        for r in results:
            r.pop("canonical_pipeline", None)
        return results


class WikiGraphQuery(AgentTool):
    """Fetch a wiki node's content and its neighbors."""

    name = "wiki_graph_query"
    description = (
        "Fetch a wiki knowledge graph node by ID. Returns the node's full documentation "
        "and its outgoing edges (neighbors). Use this to traverse the graph: "
        "task → stages (via canonical_pipeline) → methods (via modality edge) → "
        "tools (via 'implements' edge) → parameters. "
        "Also use edge_type='evaluated_by' on a task node to retrieve eval tools."
    )
    parameters = {
        "type": "object",
        "properties": {
            "node_id": {
                "type": "string",
                "description": (
                    "The wiki node ID to fetch. Examples: 'rna_clustering', 'qc', "
                    "'graph_based_clustering', 'rna_cluster_leiden', 'scanpy', 'pbmc_3k'."
                ),
            },
            "edge_type": {
                "type": "string",
                "description": (
                    "Optional edge filter. Only return neighbors with this edge type. "
                    "Use 'rna', 'atac', or 'multi' on stage nodes to get modality-specific methods. "
                    "Use 'implements' on method nodes to get tools. "
                    "Use 'evaluated_by' on task nodes to get eval tools."
                ),
            },
        },
        "required": ["node_id"],
        "additionalProperties": False,
    }

    def run(self, *, node_id: str, edge_type: str | None = None, **_: Any) -> dict[str, Any]:
        try:
            return graph_query(node_id, edge_type=edge_type)
        except KeyError as exc:
            return {"error": str(exc)}


class WikiFetchResource(AgentTool):
    """Download a named external resource and return the resolved file paths.

    Use this when a tool's requires_resources field lists a resource the user
    does not yet have on disk. Present the preset options and size to the user
    first, confirm their choice and destination directory, then call this tool.
    """

    name = "wiki_fetch_resource"
    description = (
        "Download a named external resource (e.g. pyscenic_databases) to a local directory "
        "and return the resolved file paths ready to use in a DAG plan. "
        "Call this after the user confirms which preset they want and where to save the files. "
        "Returns a dict with the parameter names mapped to their local file paths "
        "(e.g. tf_list_path, cistarget_db_paths, motif_annotations_path for pyscenic_databases)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "resource_id": {
                "type": "string",
                "description": (
                    "The wiki resource node ID (e.g. 'pyscenic_databases'). "
                    "Must match a node under wiki/resources/."
                ),
            },
            "preset": {
                "type": "string",
                "description": (
                    "Which preset to download. For pyscenic_databases: "
                    "'human', 'human_with_screen', 'human_hg19', or 'mouse'. "
                    "Read the resource node first with wiki_graph_query to see available presets."
                ),
            },
            "dest_dir": {
                "type": "string",
                "description": (
                    "Local directory where the files will be saved. "
                    "Created if it doesn't exist. Supports ~ expansion."
                ),
            },
            "skip_existing": {
                "type": "boolean",
                "description": "Skip files that already exist on disk (default true).",
            },
        },
        "required": ["resource_id", "preset", "dest_dir"],
        "additionalProperties": False,
    }

    def run(
        self,
        *,
        resource_id: str,
        preset: str,
        dest_dir: str,
        skip_existing: bool = True,
        **_: Any,
    ) -> dict[str, Any]:
        try:
            return _fetch_resource(
                resource_id=resource_id,
                preset=preset,
                dest_dir=dest_dir,
                skip_existing=skip_existing,
            )
        except Exception as exc:
            return {"error": str(exc)}


def _fetch_resource(
    *,
    resource_id: str,
    preset: str,
    dest_dir: str,
    skip_existing: bool,
) -> dict[str, Any]:
    """Look up the resource in the wiki, download the preset, return resolved paths."""
    # Read resource node from wiki to get preset definitions
    try:
        node = graph_query(resource_id)
    except KeyError:
        raise ValueError(
            f"Resource '{resource_id}' not found in wiki. "
            "Available resources: pyscenic_databases"
        )

    frontmatter = node.get("frontmatter", {})
    presets = frontmatter.get("presets", {})

    if preset not in presets:
        available = sorted(presets.keys())
        raise ValueError(
            f"Preset '{preset}' not found in resource '{resource_id}'. "
            f"Available presets: {available}"
        )

    preset_def = presets[preset]
    aliases: list[str] = preset_def["aliases"]
    resolves: dict[str, Any] = preset_def["resolves"]
    size_gb: float = preset_def.get("size_gb", 0)
    description: str = preset_def.get("description", "")

    # Import the download utility named in the resource node
    download_utility_path = frontmatter.get(
        "download_utility", "backend.tools.rna.grn.download_databases"
    )
    import importlib
    dl = importlib.import_module(download_utility_path)

    dest = Path(dest_dir).expanduser()
    print(f"\nDownloading preset '{preset}' ({description}) — ~{size_gb} GB")
    print(f"Destination: {dest}\n")

    # Download all aliases in this preset
    downloaded: dict[str, Path] = {}
    for alias in aliases:
        path = dl.download(alias, dest_dir=dest, skip_existing=skip_existing)
        downloaded[alias] = path

    # Resolve parameter names → actual paths using the preset's resolves mapping
    resolved_params: dict[str, Any] = {}
    for param_name, alias_or_list in resolves.items():
        if isinstance(alias_or_list, list):
            resolved_params[param_name] = [str(downloaded[a]) for a in alias_or_list]
        else:
            resolved_params[param_name] = str(downloaded[alias_or_list])

    print(f"\nReady to use in rna_grn_pyscenic:")
    for k, v in resolved_params.items():
        print(f"  {k}: {v}")

    return {
        "status": "ok",
        "resource_id": resource_id,
        "preset": preset,
        "dest_dir": str(dest),
        "resolved_params": resolved_params,
    }


class WikiFetchTaskGraph(AgentTool):
    """Fetch the complete subgraph for a task in a single call.

    Returns task metadata + all stages with their modality-filtered methods,
    all tools with full params, and eval tools — everything needed to produce
    a dag_plan without further wiki_graph_query calls.
    """

    name = "wiki_fetch_task_graph"
    description = (
        "Fetch the complete subgraph for a task in ONE call: "
        "task metadata → all canonical stages → modality-filtered methods → "
        "tools with full params → eval tools. "
        "Use this INSTEAD of multiple sequential wiki_graph_query calls for task traversal. "
        "Returns everything needed to produce a dag_plan in a single response."
    )
    parameters = {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": (
                    "Task node ID. Use wiki_query_tasks first to find the right ID. "
                    "Examples: 'rna_clustering', 'rna_grn', 'atac_peak_calling', 'multi_integration'."
                ),
            },
            "modality": {
                "type": "string",
                "enum": ["rna", "atac", "multi"],
                "description": "Modality to use when filtering stage → method edges.",
            },
        },
        "required": ["task_id", "modality"],
        "additionalProperties": False,
    }

    def run(self, *, task_id: str, modality: str, **_: Any) -> dict[str, Any]:
        return _fetch_task_graph(task_id=task_id, modality=modality)


def _fetch_task_graph(*, task_id: str, modality: str) -> dict[str, Any]:
    """Traverse task → stages → methods → tools → eval in one call."""
    index = get_index()

    # --- Task node ---
    try:
        task_node = index.query(task_id)
    except KeyError as exc:
        return {"error": str(exc)}

    fm = task_node["frontmatter"]
    # Stage order comes from `includes` edges in the task body (ordered as written),
    # not from a canonical_pipeline list in frontmatter.
    canonical_pipeline: list[str] = [
        e["id"] for e in task_node["neighbors"] if e["edge_type"] == "includes"
    ]

    # --- Stages (batch) ---
    stages_out: list[dict[str, Any]] = []
    for stage_id in canonical_pipeline:
        try:
            stage_node = index.query(stage_id)
        except KeyError:
            stages_out.append({"id": stage_id, "error": "stage not found"})
            continue

        # --- Methods for this stage, filtered by modality ---
        method_edges = [
            e for e in stage_node["neighbors"]
            if e["edge_type"] == modality
        ]

        methods_out: list[dict[str, Any]] = []
        for m_edge in method_edges:
            method_id = m_edge["id"]
            try:
                method_node = index.query(method_id)
            except KeyError:
                methods_out.append({"id": method_id, "error": "method not found"})
                continue

            # --- Tools for this method ---
            tool_edges = [
                e for e in method_node["neighbors"]
                if e["edge_type"] == "implements"
            ]

            tools_out: list[dict[str, Any]] = []
            for t_edge in tool_edges:
                tool_id = t_edge["id"]
                try:
                    tool_node = index.query(tool_id)
                except KeyError:
                    tools_out.append({"id": tool_id, "error": "tool not found"})
                    continue

                tool_fm = tool_node["frontmatter"]
                tools_out.append({
                    "id": tool_id,
                    "label": tool_fm.get("label", tool_id),
                    "default": tool_fm.get("default", False),
                    "params": tool_fm.get("params", {}),
                    "requires_resources": tool_fm.get("requires_resources"),
                    "content": tool_node["content"],
                })

            methods_out.append({
                "id": method_id,
                "label": method_node["frontmatter"].get("label", method_id),
                "tools": tools_out,
            })

        stages_out.append({
            "id": stage_id,
            "label": stage_node["frontmatter"].get("label", stage_id),
            "methods": methods_out,
        })

    # --- Eval tools ---
    eval_edges = [
        e for e in task_node["neighbors"]
        if e["edge_type"] == "evaluated_by"
    ]
    eval_tools_out: list[dict[str, Any]] = []
    for e_edge in eval_edges:
        eval_id = e_edge["id"]
        try:
            eval_node = index.query(eval_id)
        except KeyError:
            eval_tools_out.append({"id": eval_id, "error": "eval tool not found"})
            continue
        eval_fm = eval_node["frontmatter"]
        eval_tools_out.append({
            "id": eval_id,
            "label": eval_fm.get("label", eval_id),
            "params": eval_fm.get("params", {}),
            "content": eval_node["content"],
        })

    return {
        "task": {
            "id": task_node["id"],
            "label": fm.get("label", task_id),
            "modality": fm.get("modality", modality),
            "objective": fm.get("objective"),
            "stages_in_order": canonical_pipeline,
        },
        "stages": stages_out,
        "eval_tools": eval_tools_out,
    }


def build_wiki_tool_registry() -> AgentToolRegistry:
    """Return a registry containing all wiki tools."""
    registry = AgentToolRegistry()
    registry.register(WikiQueryTasks())
    registry.register(WikiGraphQuery())
    registry.register(WikiFetchResource())
    registry.register(WikiFetchTaskGraph())
    return registry
