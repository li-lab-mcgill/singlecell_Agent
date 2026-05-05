"""Wiki knowledge graph index.

Parses all wiki/*.md files at startup and provides graph traversal tools
for the ToolConsultant agent.

Node files live in: wiki/{type}/{id}.md
  e.g. wiki/tasks/rna_clustering.md
       wiki/stages/qc.md
       wiki/methods/graph_based_clustering.md
       wiki/tools/rna_cluster_leiden.md
       wiki/packages/scanpy.md
       wiki/resources/pbmc_3k.md

Each file has YAML frontmatter (between --- delimiters) and a body.
Edges are declared in the body as:
  - [[type/id]] [edge_type]           # schema canonical form
  - [[type/id]] edge_type             # plain text form
  - [[type/id]] modality: rna, atac   # modality edges → one entry per modality
  - Package: [[packages/id]]          # metadata edge → type="package"
  - Method: [[methods/id]]            # metadata edge → type="method"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml  # PyYAML

_WIKI_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class WikiEdge:
    target_id: str
    edge_type: str  # "rna", "atac", "multi", "implements", "evaluated_by", "package", "method"


@dataclass
class WikiNode:
    id: str
    type: str          # task, stage, method, tool, package, resource, run
    frontmatter: dict[str, Any]
    content: str       # full body text (after frontmatter)
    edges: list[WikiEdge] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Edge parsing helpers
# ---------------------------------------------------------------------------

# Matches [[type/id]] with optional trailing edge type annotation
_LINK_RE = re.compile(
    r"""
    (?P<label>[A-Za-z][A-Za-z _-]*)?    # optional label before the link (e.g. "Package: ")
    \[\[(?P<path>[^\]]+)\]\]            # [[path/id]]
    (?:                                 # optional edge annotation
      \s*\[(?P<etype_bracket>[^\]]+)\]  # [edge_type] bracket form
      |
      \s+(?P<etype_text>[^\n\[]+)       # plain text form (up to newline or next [[ )
    )?
    """,
    re.VERBOSE,
)

_MODALITY_KEYWORDS = {"rna", "atac", "multi"}


def _parse_edges(content: str) -> list[WikiEdge]:
    """Extract all edges from a node's body text."""
    edges: list[WikiEdge] = []
    for m in _LINK_RE.finditer(content):
        path = m.group("path").strip()
        # Extract the id: last component of the path (after final /)
        target_id = path.rsplit("/", 1)[-1].strip()

        # Determine edge type
        etype_bracket = m.group("etype_bracket")
        etype_text = m.group("etype_text")
        label = (m.group("label") or "").strip().lower().rstrip(": ")

        if etype_bracket:
            raw_etype = etype_bracket.strip()
        elif etype_text:
            raw_etype = etype_text.strip()
        elif label in ("package", "method"):
            raw_etype = label
        else:
            raw_etype = ""

        # Normalise: strip trailing punctuation / noise
        raw_etype = raw_etype.rstrip(".,;")

        # Handle "modality: rna, atac, multi" → split into individual modality edges
        if raw_etype.startswith("modality:"):
            modalities_str = raw_etype[len("modality:"):].strip()
            for mod in re.split(r"[,\s]+", modalities_str):
                mod = mod.strip()
                if mod in _MODALITY_KEYWORDS:
                    edges.append(WikiEdge(target_id=target_id, edge_type=mod))
        elif raw_etype in _MODALITY_KEYWORDS:
            edges.append(WikiEdge(target_id=target_id, edge_type=raw_etype))
        elif raw_etype:
            edges.append(WikiEdge(target_id=target_id, edge_type=raw_etype))
        else:
            # No edge type annotation — use the node type from the path prefix as edge type
            node_type_prefix = path.split("/")[0].rstrip("s")  # "methods" → "method"
            edges.append(WikiEdge(target_id=target_id, edge_type=node_type_prefix))

    return edges


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split YAML frontmatter from body. Returns (frontmatter_dict, body)."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        fm = {}
    body = text[m.end():]
    return fm, body


# ---------------------------------------------------------------------------
# WikiIndex
# ---------------------------------------------------------------------------

class WikiIndex:
    """Scans wiki/ directory and builds an in-memory node graph."""

    def __init__(self, wiki_dir: Path = _WIKI_DIR) -> None:
        self._nodes: dict[str, WikiNode] = {}
        self._build(wiki_dir)

    def _build(self, wiki_dir: Path) -> None:
        for md_path in sorted(wiki_dir.rglob("*.md")):
            # Skip the schema file (not a node)
            if md_path.name == "schema.md":
                continue
            text = md_path.read_text(encoding="utf-8")
            fm, body = _parse_frontmatter(text)
            node_id = fm.get("id") or md_path.stem
            node_type = fm.get("type") or md_path.parent.name.rstrip("s")
            edges = _parse_edges(body)
            node = WikiNode(
                id=node_id,
                type=node_type,
                frontmatter=fm,
                content=body.strip(),
                edges=edges,
            )
            self._nodes[node_id] = node

    # ------------------------------------------------------------------
    # Public query API
    # ------------------------------------------------------------------

    def get_node(self, node_id: str) -> WikiNode | None:
        return self._nodes.get(node_id)

    def query(
        self,
        node_id: str,
        *,
        edge_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Returns:
          {
            "id": str,
            "type": str,
            "content": str,         # body text of the node
            "frontmatter": dict,    # parsed YAML frontmatter
            "neighbors": [
              {"id": str, "edge_type": str},
              ...
            ]
          }
        Raises KeyError if node_id not found.
        """
        node = self._nodes.get(node_id)
        if node is None:
            available = sorted(self._nodes.keys())
            raise KeyError(
                f"Wiki node '{node_id}' not found. "
                f"Available ({len(available)}): {available[:20]}"
                f"{'...' if len(available) > 20 else ''}"
            )
        neighbors = node.edges
        if edge_type is not None:
            neighbors = [e for e in neighbors if e.edge_type == edge_type]
        return {
            "id": node.id,
            "type": node.type,
            "content": node.content,
            "frontmatter": node.frontmatter,
            "neighbors": [{"id": e.target_id, "edge_type": e.edge_type} for e in neighbors],
        }

    def query_tasks(self, *, modality: str | None = None) -> list[dict[str, Any]]:
        """
        Returns all task nodes, optionally filtered by modality.
        Each entry: {"id": str, "label": str, "modality": str, "canonical_pipeline": list}
        """
        results = []
        for node in self._nodes.values():
            if node.type != "task":
                continue
            node_modality = node.frontmatter.get("modality", "")
            if modality and node_modality != modality:
                continue
            results.append({
                "id": node.id,
                "label": node.frontmatter.get("label", node.id),
                "modality": node_modality,
                "canonical_pipeline": node.frontmatter.get("canonical_pipeline", []),
            })
        results.sort(key=lambda x: x["id"])
        return results

    def list_nodes(self, *, node_type: str | None = None) -> list[str]:
        """List all node IDs, optionally filtered by type."""
        return sorted(
            nid for nid, node in self._nodes.items()
            if node_type is None or node.type == node_type
        )

    @property
    def node_count(self) -> int:
        return len(self._nodes)


# ---------------------------------------------------------------------------
# Singleton — built once on first import
# ---------------------------------------------------------------------------

_index: WikiIndex | None = None


def get_index() -> WikiIndex:
    global _index
    if _index is None:
        _index = WikiIndex()
    return _index


# ---------------------------------------------------------------------------
# Convenience functions (callable as tools)
# ---------------------------------------------------------------------------

def graph_query(node_id: str, edge_type: str | None = None) -> dict[str, Any]:
    """
    Retrieve a wiki node and its neighbors.

    Args:
        node_id:   The wiki node ID (e.g. "rna_clustering", "qc", "leiden").
        edge_type: Optional filter — only return neighbors with this edge type
                   (e.g. "rna", "atac", "implements", "evaluated_by").

    Returns:
        {
          "id": str,
          "type": str,
          "content": str,
          "frontmatter": dict,
          "neighbors": [{"id": str, "edge_type": str}, ...]
        }
    """
    return get_index().query(node_id, edge_type=edge_type)


def query_tasks(modality: str | None = None) -> list[dict[str, Any]]:
    """
    List all available task nodes.

    Args:
        modality: Optional filter — "rna", "atac", or "multi".

    Returns:
        List of {"id", "label", "modality", "canonical_pipeline"} dicts.
    """
    return get_index().query_tasks(modality=modality)
