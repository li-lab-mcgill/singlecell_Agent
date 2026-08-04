"""Tools for the Analyzer Panel panelists.

Tool registries:
  build_results_interpreter_registry()  → retrieve_literature, fetch_paper_content,
                                          interpret_figure
  build_literature_grounder_registry()  → retrieve_literature, fetch_paper_content
  build_database_validator_registry()   → retrieve_literature, fetch_paper_content,
                                          enrichr_enrichment, omnipath_interactions,
                                          string_network
"""

from __future__ import annotations

import base64
import json
import re
import time
from pathlib import Path
from typing import Any

import requests

from agents.tool_base import AgentTool, AgentToolRegistry
from agents.panelist_tools import RetrieveLiteratureTool, FetchPaperWikiTool, FetchPaperContentTool
from agents.paper_judge import PaperJudge
from rag.literature_retriever import LiteratureRetriever

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# interpret_figure — VLM call (GPT-4o vision)
# ---------------------------------------------------------------------------

class InterpretFigureTool(AgentTool):
    """Read a figure file and return a natural language interpretation via VLM."""

    name = "interpret_figure"
    description = (
        "Interpret a figure or plot produced by the analysis pipeline. "
        "Provide the absolute path to the figure file (PNG, JPEG, GIF, or WebP) and a "
        "context string describing what the figure is supposed to show "
        "(from the research plan's required_visualizations). "
        "Returns a structured interpretation: what the figure shows, key "
        "patterns, quality flags, and whether it supports the hypothesis."
    )
    parameters = {
        "type": "object",
        "properties": {
            "figure_path": {
                "type": "string",
                "description": "Absolute path to the figure file (PNG, JPEG, GIF, or WebP). SVG is not supported — convert to PNG first.",
            },
            "context": {
                "type": "string",
                "description": (
                    "What this figure is supposed to show, from the research plan. "
                    "E.g. 'UMAP colored by cluster and condition to verify batch correction'."
                ),
            },
        },
        "required": ["figure_path", "context"],
        "additionalProperties": False,
    }

    def __init__(self, *, client: Any, engine_name: str = "gpt-4o"):
        self._client = client
        self._engine_name = engine_name

    def run(self, *, figure_path: str, context: str, **_: Any) -> dict[str, Any]:
        path = Path(figure_path)
        if not path.exists():
            return {"error": f"Figure not found: {figure_path}"}

        suffix = path.suffix.lower()
        # GPT-4o vision supports PNG, JPEG, GIF, WebP only — not SVG
        if suffix == ".svg":
            return {
                "error": (
                    "SVG format is not supported by the VLM. "
                    "Re-save the figure as PNG before calling interpret_figure()."
                ),
                "figure_path": figure_path,
            }
        elif suffix in {".jpg", ".jpeg"}:
            mime = "image/jpeg"
        elif suffix in {".gif"}:
            mime = "image/gif"
        elif suffix in {".webp"}:
            mime = "image/webp"
        else:
            mime = "image/png"

        try:
            image_data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
        except Exception as exc:
            return {"error": f"Could not read figure: {exc}"}

        prompt = (
            f"You are interpreting a figure from a single-cell genomics analysis.\n\n"
            f"Context (what this figure should show):\n{context}\n\n"
            f"Describe what the figure actually shows. Be specific about:\n"
            f"- What patterns, clusters, or distributions are visible\n"
            f"- Whether the figure quality is adequate for interpretation\n"
            f"- Whether the result supports, contradicts, or is ambiguous about the hypothesis\n\n"
            f"Return ONLY a JSON object:\n"
            f'{{"description": "...", "key_patterns": ["..."], '
            f'"quality_flags": ["..."], "supports_hypothesis": "yes|partial|no|unclear"}}'
        )

        try:
            response = self._client.responses.create(
                model=self._engine_name,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {
                                "type": "input_image",
                                "image_url": f"data:{mime};base64,{image_data}",
                                "detail": "high",
                            },
                        ],
                    }
                ],
            )
            # Extract text — try output_text shortcut first, then iterate output items
            text = str(getattr(response, "output_text", "") or "").strip()
            if not text:
                for item in getattr(response, "output", []):
                    content = getattr(item, "content", None)
                    if isinstance(content, str) and content.strip():
                        text = content.strip()
                        break
                    if isinstance(content, list):
                        for part in content:
                            t = getattr(part, "text", None)
                            if isinstance(t, str) and t.strip():
                                text = t.strip()
                                break
                    if text:
                        break
            return _parse_json_safe(text, figure_path=figure_path)
        except Exception as exc:
            return {"error": f"VLM call failed: {exc}", "figure_path": figure_path}


# ---------------------------------------------------------------------------
# enrichr_enrichment — Enrichr API
# ---------------------------------------------------------------------------

class EnrichrEnrichmentTool(AgentTool):
    """Run gene set enrichment via the Enrichr API."""

    name = "enrichr_enrichment"
    description = (
        "Submit a gene list to Enrichr and return enriched terms from the specified "
        "libraries. Use this to:\n"
        "- Validate TF-target claims: library='ChEA_2022'\n"
        "- Validate pathway claims: library='GO_Biological_Process_2023' or 'KEGG_2021_Human'\n"
        "- Validate cell type annotations: library='CellMarker_2024'\n"
        "Returns top enriched terms with p-values and overlapping genes."
    )
    parameters = {
        "type": "object",
        "properties": {
            "gene_list": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of gene symbols to enrich (e.g. DE genes, cluster markers).",
            },
            "libraries": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Enrichr library names to query. "
                    "Options: 'ChEA_2022', 'GO_Biological_Process_2023', "
                    "'KEGG_2021_Human', 'Reactome_2022', 'CellMarker_2024'."
                ),
            },
            "top_k": {
                "type": "integer",
                "description": "Number of top enriched terms to return per library (default 10).",
                "default": 10,
            },
        },
        "required": ["gene_list", "libraries"],
        "additionalProperties": False,
    }

    _BASE = "https://maayanlab.cloud/Enrichr"

    def run(
        self,
        *,
        gene_list: list[str],
        libraries: list[str],
        top_k: int = 10,
        **_: Any,
    ) -> dict[str, Any]:
        if not gene_list:
            return {"error": "gene_list is empty"}
        if not libraries:
            return {"error": "libraries is empty"}

        # Step 1: submit gene list
        try:
            resp = requests.post(
                f"{self._BASE}/addList",
                files={"list": (None, "\n".join(gene_list)), "description": (None, "analyzer_query")},
                timeout=30,
            )
            resp.raise_for_status()
            user_list_id = resp.json().get("userListId")
        except Exception as exc:
            return {"error": f"Enrichr addList failed: {exc}"}

        if not user_list_id:
            return {"error": "Enrichr did not return userListId"}

        # Step 2: query each library
        results: dict[str, Any] = {}
        for lib in libraries:
            try:
                time.sleep(0.3)  # polite rate limit
                resp = requests.get(
                    f"{self._BASE}/enrich",
                    params={"userListId": user_list_id, "backgroundType": lib},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json().get(lib, [])
                # Each entry: [rank, term, p-value, z-score, combined_score, genes, adj_p]
                top_terms = []
                for entry in data[:top_k]:
                    if len(entry) >= 7:
                        top_terms.append({
                            "term": entry[1],
                            "p_value": entry[2],
                            "adjusted_p_value": entry[6],
                            "combined_score": entry[4],
                            "overlapping_genes": entry[5],
                        })
                results[lib] = top_terms
            except Exception as exc:
                results[lib] = {"error": str(exc)}

        return {
            "gene_list_size": len(gene_list),
            "user_list_id": user_list_id,
            "results": results,
        }


# ---------------------------------------------------------------------------
# omnipath_interactions — OmniPath REST API
# ---------------------------------------------------------------------------

class OmniPathInteractionsTool(AgentTool):
    """Query OmniPath for directed biological interactions."""

    name = "omnipath_interactions"
    description = (
        "Query OmniPath for directed biological interactions between genes. "
        "Use this to validate specific claims:\n"
        "- TF→target gene edges: interaction_type='tf_target'\n"
        "- Ligand→receptor pairs: interaction_type='ligand_receptor'\n"
        "- General signaling: interaction_type='signaling'\n"
        "Provide source_genes and/or target_genes to filter interactions."
    )
    parameters = {
        "type": "object",
        "properties": {
            "source_genes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Source gene symbols (e.g. TF names, ligand names).",
            },
            "target_genes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Target gene symbols (e.g. target genes, receptor names).",
            },
            "interaction_type": {
                "type": "string",
                "enum": ["tf_target", "ligand_receptor", "signaling"],
                "description": "Type of interaction to query.",
            },
        },
        "required": ["interaction_type"],
        "additionalProperties": False,
    }

    _BASE = "https://omnipathdb.org"
    _DATASET_MAP = {
        "tf_target": "tf_target",
        "ligand_receptor": "ligrecextra",
        "signaling": "omnipath",
    }

    def run(
        self,
        *,
        interaction_type: str,
        source_genes: list[str] | None = None,
        target_genes: list[str] | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        # Require at least one gene filter — querying with no filter returns
        # the entire OmniPath database (hundreds of thousands of rows)
        if not source_genes and not target_genes:
            return {
                "error": (
                    "At least one of source_genes or target_genes must be provided. "
                    "Querying with no gene filter would return the entire database."
                )
            }

        dataset = self._DATASET_MAP.get(interaction_type, "omnipath")
        params: dict[str, Any] = {
            "datasets": dataset,
            "fields": "sources,references",
            "format": "json",
        }
        if source_genes:
            params["sources"] = ",".join(source_genes)
        if target_genes:
            params["targets"] = ",".join(target_genes)

        try:
            resp = requests.get(
                f"{self._BASE}/interactions",
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            return {"error": f"OmniPath query failed: {exc}"}

        if not isinstance(data, list):
            return {"error": "Unexpected OmniPath response format", "raw": str(data)[:500]}

        interactions = []
        for entry in data[:50]:  # cap at 50
            interactions.append({
                "source": entry.get("source"),
                "target": entry.get("target"),
                "is_stimulation": entry.get("is_stimulation"),
                "is_inhibition": entry.get("is_inhibition"),
                "n_references": entry.get("n_references", 0),
                "sources": entry.get("sources", ""),
            })

        return {
            "interaction_type": interaction_type,
            "n_interactions_found": len(interactions),
            "interactions": interactions,
        }


# ---------------------------------------------------------------------------
# string_network — STRING API
# ---------------------------------------------------------------------------

class StringNetworkTool(AgentTool):
    """Query STRING for PPI network enrichment of a gene set."""

    name = "string_network"
    description = (
        "Query the STRING database to check if a gene set forms a functionally "
        "connected protein-protein interaction (PPI) network. A significant "
        "enrichment p-value indicates the genes interact more than expected by "
        "chance — useful for validating cluster coherence or pathway membership. "
        "Species: 9606 (human), 10090 (mouse)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "gene_list": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Gene symbols to check for PPI network enrichment.",
            },
            "species": {
                "type": "integer",
                "description": "NCBI taxon ID: 9606 (human) or 10090 (mouse).",
            },
        },
        "required": ["gene_list", "species"],
        "additionalProperties": False,
    }

    _BASE = "https://string-db.org/api/json"

    def run(
        self,
        *,
        gene_list: list[str],
        species: int = 9606,
        **_: Any,
    ) -> dict[str, Any]:
        if not gene_list:
            return {"error": "gene_list is empty"}

        # STRING API expects gene identifiers separated by \r in the POST body.
        # requests form-encodes \r as %0D, which the API correctly decodes.
        identifiers = "\r".join(gene_list)

        try:
            # Get network stats (enrichment)
            resp = requests.post(
                f"{self._BASE}/ppi_enrichment",
                data={
                    "identifiers": identifiers,
                    "species": species,
                    "caller_identity": "singlecell_agent",
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            return {"error": f"STRING query failed: {exc}"}

        if not data:
            return {"n_genes": len(gene_list), "species": species, "result": "no data returned"}

        entry = data[0] if isinstance(data, list) else data
        return {
            "n_genes": len(gene_list),
            "species": species,
            "n_nodes": entry.get("number_of_nodes"),
            "n_edges": entry.get("number_of_edges"),
            "expected_edges": entry.get("expected_number_of_edges"),
            "average_node_degree": entry.get("average_node_degree"),
            "local_clustering_coefficient": entry.get("local_clustering_coefficient"),
            "ppi_enrichment_pvalue": entry.get("p_value"),
            "interpretation": (
                "Network is significantly enriched (more interactions than expected by chance)"
                if float(entry.get("p_value", 1.0)) < 0.05
                else "Network is NOT significantly enriched"
            ),
        }


# ---------------------------------------------------------------------------
# Registry builders
# ---------------------------------------------------------------------------

def build_results_interpreter_registry(
    *,
    retriever: LiteratureRetriever,
    judge: PaperJudge,
    client: Any,
    vlm_engine: str = "gpt-4o",
) -> AgentToolRegistry:
    """Tools for ResultsInterpreter: RAG (biologist role) + figure interpretation."""
    registry = AgentToolRegistry()
    # Uses "biologist" role — ResultsInterpreter retrieves biological context
    # to help interpret numerical findings (e.g. "is this ARI good for this cell type?")
    registry.register(RetrieveLiteratureTool(retriever=retriever, judge=judge, role="biologist"))
    registry.register(FetchPaperWikiTool())
    registry.register(FetchPaperContentTool(retriever=retriever))
    registry.register(InterpretFigureTool(client=client, engine_name=vlm_engine))
    return registry


def build_literature_grounder_registry(
    *,
    retriever: LiteratureRetriever,
    judge: PaperJudge,
) -> AgentToolRegistry:
    """Tools for LiteratureGrounder: RAG with grounder role.

    "grounder" role asks PaperJudge whether a paper confirms, contradicts,
    or contextualizes a specific finding — more targeted than "narrator".
    """
    registry = AgentToolRegistry()
    registry.register(RetrieveLiteratureTool(retriever=retriever, judge=judge, role="grounder"))
    registry.register(FetchPaperWikiTool())
    registry.register(FetchPaperContentTool(retriever=retriever))
    return registry


def build_database_validator_registry(
    *,
    retriever: LiteratureRetriever,
    judge: PaperJudge,
) -> AgentToolRegistry:
    """Tools for DatabaseValidator: RAG (validator role) + biological databases.

    "validator" role asks PaperJudge whether a paper describes regulatory
    relationships or experimental evidence to validate a biological claim.
    """
    registry = AgentToolRegistry()
    registry.register(RetrieveLiteratureTool(retriever=retriever, judge=judge, role="validator"))
    registry.register(FetchPaperWikiTool())
    registry.register(FetchPaperContentTool(retriever=retriever))
    registry.register(EnrichrEnrichmentTool())
    registry.register(OmniPathInteractionsTool())
    registry.register(StringNetworkTool())
    return registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_json_safe(text: str, **extra: Any) -> dict[str, Any]:
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        payload = json.loads(cleaned)
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return {"raw": text, **extra}
