"""Paper wiki index — persistent graph of retrieved literature.

Parallel to the tool wiki (wiki/index.py) but for papers. Grows dynamically
as sessions run — new papers are added when fetched and judged relevant.

Structure:
  wiki/papers/{paper_id}.md   ← one markdown file per paper
  (no separate JSON — the md files are the store, index is in-memory)

Two edge types:
  task  → paper    stored in paper frontmatter: tasks: [task_id, ...]
  paper → paper    stored in paper frontmatter: extends: [paper_id, ...]

The index is rebuilt from md files at startup. New papers can be added at
runtime (thread-safe). Papers already in the wiki are never rewritten.

Usage:
    from wiki.paper_index import get_paper_index

    idx = get_paper_index()
    papers = idx.get_papers_for_task("rna_cell_type_annotation")
    paper  = idx.get_paper("pubmed_38901234")
    chain  = idx.get_extends_chain("pubmed_38901234", max_depth=2)
    added  = idx.add_paper(paper_id="...", md_content="...")
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_PAPERS_DIR = Path(__file__).parent / "papers"
_PAPERS_DIR.mkdir(exist_ok=True)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class PaperNode:
    paper_id: str
    title: str
    tasks: list[str]          # task IDs from tool wiki taxonomy
    extends: list[str]        # paper_ids this paper extends
    added: str                # ISO date string
    session: str              # session_id when added
    content: str              # full body text (after frontmatter)
    md_path: Path
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# PaperWikiIndex
# ---------------------------------------------------------------------------

class PaperWikiIndex:
    """In-memory index of all papers in wiki/papers/.

    Thread-safe: concurrent sessions can add papers simultaneously.
    """

    def __init__(self, papers_dir: Path = _PAPERS_DIR) -> None:
        self._dir = papers_dir
        self._lock = threading.Lock()
        self._papers: dict[str, PaperNode] = {}
        self._task_to_papers: dict[str, list[str]] = {}  # task_id → [paper_id]
        self._build()

    def _build(self) -> None:
        for md_path in sorted(self._dir.glob("*.md")):
            self._load_file(md_path)

    def _load_file(self, md_path: Path) -> PaperNode | None:
        try:
            text = md_path.read_text(encoding="utf-8")
        except Exception:
            return None
        fm, body = _parse_frontmatter(text)
        paper_id = str(fm.get("paper_id") or md_path.stem)
        title = str(fm.get("title") or "")
        tasks = _as_list(fm.get("tasks", []))
        extends = _as_list(fm.get("extends", []))
        added = str(fm.get("added") or "")
        session = str(fm.get("session") or "")
        node = PaperNode(
            paper_id=paper_id,
            title=title,
            tasks=tasks,
            extends=extends,
            added=added,
            session=session,
            content=body.strip(),
            md_path=md_path,
            metadata=dict(fm),
        )
        self._papers[paper_id] = node
        for task_id in tasks:
            self._task_to_papers.setdefault(task_id, [])
            if paper_id not in self._task_to_papers[task_id]:
                self._task_to_papers[task_id].append(paper_id)
        return node

    # ------------------------------------------------------------------
    # Public read API
    # ------------------------------------------------------------------

    def has_paper(self, paper_id: str) -> bool:
        return paper_id in self._papers

    def get_paper(self, paper_id: str) -> dict[str, Any] | None:
        node = self._papers.get(paper_id)
        if node is None:
            return None
        return _node_to_dict(node)

    def get_papers_for_task(self, task_id: str) -> list[dict[str, Any]]:
        """Return all papers linked to a task node."""
        paper_ids = self._task_to_papers.get(task_id, [])
        result = []
        for pid in paper_ids:
            node = self._papers.get(pid)
            if node is not None:
                result.append(_node_to_dict(node))
        return result

    def get_extends_chain(
        self,
        paper_id: str,
        *,
        max_depth: int = 2,
    ) -> list[dict[str, Any]]:
        """Return papers reachable via extends edges from paper_id.

        Traverses: paper_id → papers it extends → papers those extend, up to max_depth.
        Returns the chain as a flat list (excluding paper_id itself), deduplicated.
        """
        visited: set[str] = {paper_id}
        queue: list[tuple[str, int]] = [(paper_id, 0)]
        result: list[dict[str, Any]] = []
        while queue:
            current_id, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            node = self._papers.get(current_id)
            if node is None:
                continue
            for ext_id in node.extends:
                if ext_id in visited:
                    continue
                visited.add(ext_id)
                ext_node = self._papers.get(ext_id)
                if ext_node is not None:
                    result.append(_node_to_dict(ext_node))
                    queue.append((ext_id, depth + 1))
        return result

    def get_papers_extending(self, paper_id: str) -> list[dict[str, Any]]:
        """Return all papers that extend the given paper_id (reverse edge)."""
        result = []
        for node in self._papers.values():
            if paper_id in node.extends:
                result.append(_node_to_dict(node))
        return result

    def list_task_ids(self) -> list[str]:
        """All task IDs that have at least one paper."""
        return sorted(self._task_to_papers.keys())

    def query_papers(
        self,
        *,
        user_question: str = "",
        data_summary: str = "",
        role: str = "",
        retrieval_goal: str = "",
        retrieval_intent: str = "",
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Return a small role/intent-scoped set of structured paper wiki entries.

        This is intentionally lightweight: the panelist remains responsible for
        judging whether the returned wiki entries are sufficient. The query only
        limits context size and ranks likely-relevant entries.
        """
        limit = max(1, min(int(top_k or 5), 10))
        query_text = " ".join(
            part
            for part in [user_question, data_summary, role, retrieval_goal, retrieval_intent]
            if str(part).strip()
        )
        query_tokens = _tokens(query_text)
        role_tokens = _role_tokens(role)
        scored: list[tuple[float, PaperNode]] = []
        for node in self._papers.values():
            haystack = " ".join(
                [
                    node.title,
                    " ".join(node.tasks),
                    str(node.metadata.get("retrieval_goals") or ""),
                    str(node.metadata.get("retrieval_intents") or ""),
                    node.content,
                ]
            )
            tokens = _tokens(haystack)
            score = float(len(query_tokens & tokens))
            if role_tokens and role_tokens & tokens:
                score += 2.0
            if retrieval_goal and retrieval_goal in str(node.metadata.get("retrieval_goals") or ""):
                score += 3.0
            if not query_tokens or score > 0:
                scored.append((score, node))
        scored.sort(key=lambda item: (item[0], item[1].added, item[1].title), reverse=True)
        return [_node_to_dict(node) for _, node in scored[:limit]]

    @property
    def paper_count(self) -> int:
        return len(self._papers)

    # ------------------------------------------------------------------
    # Public write API (thread-safe)
    # ------------------------------------------------------------------

    def add_paper(self, *, paper_id: str, md_content: str) -> bool:
        """Write a new paper md file and update the index.

        Returns True if paper was added, False if it already existed.
        md_content must be a complete markdown string including frontmatter.
        """
        with self._lock:
            if paper_id in self._papers:
                return False
            md_path = self._dir / f"{paper_id}.md"
            md_path.write_text(md_content, encoding="utf-8")
            self._load_file(md_path)
            return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, text[m.end():]


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _node_to_dict(node: PaperNode) -> dict[str, Any]:
    return {
        "paper_id": node.paper_id,
        "title": node.title,
        "tasks": node.tasks,
        "extends": node.extends,
        "added": node.added,
        "session": node.session,
        "content": node.content,
        "source_ids": node.metadata.get("source_ids", {}),
        "doi": node.metadata.get("doi", ""),
        "url": node.metadata.get("url", ""),
        "full_text_status": node.metadata.get("full_text_status", ""),
        "retrieval_goals": _as_list(node.metadata.get("retrieval_goals", [])),
        "retrieval_intents": _as_list(node.metadata.get("retrieval_intents", [])),
    }


def _tokens(text: str) -> set[str]:
    stop = {
        "the", "and", "for", "with", "from", "that", "this", "into", "using",
        "single", "cell", "cells", "paper", "study", "analysis", "dataset",
    }
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9]+", str(text or "").lower())
        if len(token) >= 4 and token not in stop
    }


def _role_tokens(role: str) -> set[str]:
    role = str(role or "").lower().strip()
    if role == "biologist":
        return {"biology", "biological", "marker", "markers", "pathway", "state", "disease"}
    if role == "statistician":
        return {"statistical", "statistics", "covariate", "confounder", "donor", "patient", "model"}
    if role == "bioinformatician":
        return {"method", "workflow", "tool", "benchmark", "computational", "algorithm"}
    return set()


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_index: PaperWikiIndex | None = None
_index_lock = threading.Lock()


def get_paper_index() -> PaperWikiIndex:
    global _index
    if _index is None:
        with _index_lock:
            if _index is None:
                _index = PaperWikiIndex()
    return _index
