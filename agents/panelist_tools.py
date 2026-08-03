"""Tools available to Scientist panel panelists.

Each panelist agent (Biologist, Statistician, Bioinformatician) is a
ToolCallingAgentRunner with literature tools registered:

  search_paper_wiki(retrieval_intent, retrieval_goal, requirements, background)
    -> scoped lookup over accumulated paper memory

  retrieve_literature(retrieval_intent, retrieval_goal, requirements, background)
    → fresh external retrieval only
    → runs LiteratureRetriever + PaperJudge
    → returns useful judged canonical summaries
    → persists only high-confidence useful papers to the paper wiki

  fetch_paper_wiki(paper_id)
    → reads the curated paper wiki summary for a known paper

  fetch_paper_content(paper_id, section=None, query=None, max_chars=4000)
    → drills into detailed stored/full-text content for a known paper

The tools are instantiated with shared LiteratureRetriever, PaperJudge,
and optionally PaperMDWriter instances.

Usage:
    registry = build_panelist_tool_registry(
        role="biologist",
        retriever=retriever,
        judge=judge,
        paper_md_writer=writer,   # optional — enables wiki growth
    )
    # pass registry.tool_specs() and registry.executor() to ToolCallingAgentRunner
"""

from __future__ import annotations

import threading
import re
import uuid
from typing import Any

from agents.tool_base import AgentTool, AgentToolRegistry
from agents.paper_judge import PaperJudge
from rag.literature_retriever import LiteratureRetriever
from wiki.paper_index import get_paper_index

# PaperMDWriter is imported lazily to avoid circular imports at module load.
# Persistence is intentionally synchronous here: a successful retrieval should
# not fail because a process is shutting down while scheduling a background write.

_PERSIST_TO_WIKI_THRESHOLD = 0.75


def _clamped_int(value: Any, *, default: int, lower: int, upper: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(lower, min(parsed, upper))


# ---------------------------------------------------------------------------
# retrieve_literature
# ---------------------------------------------------------------------------

class RetrieveLiteratureTool(AgentTool):
    """Retrieve and judge literature relevant to the panelist's retrieval intent.

    Wraps the full pipeline:
    keyword gen → fetch (PubMed + S2 + OpenAlex) → embed → HyDE rerank →
    RRF → paper summaries → PaperJudge

    Returns labeled paper summaries. Multiple calls allowed per round —
    each call is an independent retrieval with its own base_query.
    """

    name = "retrieve_literature"
    description = (
        "Run fresh external retrieval for one explicit role-specific retrieval intent. "
        "Use search_paper_wiki first when accumulated memory may already cover the intent. "
        "Provide retrieval_intent, retrieval_goal, requirements, and background. Returns only "
        "useful judged canonical paper summaries plus a retrieval_context_id for duplicate avoidance."
    )
    parameters = {
        "type": "object",
        "properties": {
            "search_query": {
                "type": "string",
                "description": (
                    "Concrete search phrase generated from the retrieval intent. "
                    "Example: 'regulatory T cell Treg markers IBD inflammation single cell'"
                ),
            },
            "base_query": {
                "type": "string",
                "description": "Deprecated compatibility spelling for search_query.",
            },
            "retrieval_context_id": {
                "type": "string",
                "description": "Optional context ID from a previous retrieve_literature call in this panelist loop.",
            },
            "retrieval_intent": {
                "type": "string",
                "description": "The specific question you need literature to answer.",
            },
            "retrieval_goal": {
                "type": "string",
                "enum": [
                    "method_selection",
                    "evidence_pattern",
                    "prior_findings",
                    "contradiction",
                    "validation",
                    "extension_opportunity",
                    "broad_background",
                ],
                "description": "Why this literature is needed.",
            },
            "requirements": {
                "type": "string",
                "description": (
                    "Current research-plan constraints the paper should be judged against. "
                    "Used for judging/reranking, not as the default external search query."
                ),
            },
            "background": {
                "type": "string",
                "description": (
                    "Context about the dataset and question to help generate targeted queries. "
                    "Include: tissue type, disease, modality, approximate cell count, "
                    "key metadata columns, the user's biological question."
                ),
            },
            "top_k": {
                "type": "integer",
                "description": "Maximum number of papers to return (default 8).",
            },
            "exclude_ids": {
                "type": "object",
                "description": "Known papers to exclude from this fresh retrieval.",
                "properties": {
                    "paper_ids": {"type": "array", "items": {"type": "string"}},
                    "dois": {"type": "array", "items": {"type": "string"}},
                    "pmids": {"type": "array", "items": {"type": "string"}},
                    "pmcids": {"type": "array", "items": {"type": "string"}},
                    "semantic_scholar_ids": {"type": "array", "items": {"type": "string"}},
                    "openalex_ids": {"type": "array", "items": {"type": "string"}},
                    "normalized_titles": {"type": "array", "items": {"type": "string"}},
                },
                "additionalProperties": False,
            },
        },
        "required": ["retrieval_intent", "retrieval_goal", "requirements", "background"],
        "additionalProperties": False,
    }

    def __init__(
        self,
        *,
        retriever: LiteratureRetriever,
        judge: PaperJudge,
        role: str,
        paper_md_writer: Any | None = None,
    ):
        self._retriever = retriever
        self._judge = judge
        self._role = role.lower().strip()
        self._writer = paper_md_writer  # PaperMDWriter | None
        self._contexts: dict[str, set[str]] = {}
        self._lock = threading.Lock()

    def run(
        self,
        *,
        retrieval_intent: str | None = None,
        retrieval_goal: str | None = None,
        retrieval_context_id: str | None = None,
        requirements: str = "",
        search_query: str | None = None,
        base_query: str | None = None,
        background: str,
        exclude_ids: dict[str, Any] | None = None,
        top_k: int = 8,
        **_: Any,
    ) -> dict[str, Any]:
        retrieval_intent = str(retrieval_intent or base_query or "").strip()
        retrieval_goal = _normalize_retrieval_goal(retrieval_goal)
        base_query = str(search_query or base_query or retrieval_intent).strip()
        retrieval_context_id = str(retrieval_context_id or "").strip() or f"litctx_{uuid.uuid4().hex[:12]}"
        limit = _clamped_int(top_k, default=8, lower=1, upper=20)

        # Step 1: retrieve + summarize fresh candidates.
        fresh_papers = self._retriever.retrieve(
            retrieval_intent=retrieval_intent,
            retrieval_goal=retrieval_goal,
            base_query=base_query,
            background=_join_context(background=background, requirements=requirements),
            role=self._role,
            question=retrieval_intent,
            top_k=max(limit * 2, limit),
        )
        fresh_papers = _deduplicate_papers(fresh_papers)
        seen_before = self._seen_for_context(retrieval_context_id)
        exclude_keys = seen_before | _exclude_keys(exclude_ids or {})
        self._record_seen(retrieval_context_id, fresh_papers)
        fresh_papers = [p for p in fresh_papers if _paper_dedupe_key(p) not in exclude_keys]
        if not fresh_papers:
            return {
                "retrieval_context_id": retrieval_context_id,
                "retrieval_intent": retrieval_intent,
                "retrieval_goal": retrieval_goal,
                "papers": [],
                "excluded_count": len(exclude_keys),
            }

        # Step 2: PaperJudge, one paper at a time internally.
        labeled = self._judge.judge(
            papers=fresh_papers,
            role=self._role,
            retrieval_intent=retrieval_intent,
            retrieval_goal=retrieval_goal,
            base_query=base_query,
            threshold=0.60,
        )

        # Step 3: canonicalize and return only useful judged summaries.
        canonicalized = [
            _canonicalize_judged_paper(
                p,
                retrieval_intent=retrieval_intent,
                retrieval_goal=retrieval_goal,
                requirements=requirements,
                source="fresh_retrieval",
            )
            for p in labeled
        ]
        useful = [p for p in canonicalized if _should_return_to_panelist(p)]
        useful = _deduplicate_papers(useful, use_title_fallback=True)[:limit]

        # Step 4: write only high-confidence useful fresh papers to wiki in background.
        if self._writer is not None and useful:
            writer = self._writer
            papers_to_write = [
                {
                    **p,
                    "retrieval_goal": retrieval_goal,
                    "retrieval_intent": retrieval_intent,
                    "base_query": base_query,
                }
                for p in useful
                if _should_persist_to_wiki(p)
            ]
            persistence_error = ""
            if papers_to_write:
                try:
                    writer.write_batch(papers_to_write)
                except Exception as exc:  # pragma: no cover - persistence should not poison retrieval
                    persistence_error = str(exc)
        else:
            persistence_error = ""

        output = {
            "retrieval_context_id": retrieval_context_id,
            "retrieval_intent": retrieval_intent,
            "retrieval_goal": retrieval_goal,
            "papers": useful,
            "excluded_count": len(exclude_keys),
        }
        if persistence_error:
            output["persistence_error"] = persistence_error
        return output

    def _seen_for_context(self, context_id: str) -> set[str]:
        with self._lock:
            return set(self._contexts.setdefault(context_id, set()))

    def _record_seen(self, context_id: str, papers: list[dict[str, Any]]) -> None:
        with self._lock:
            seen = self._contexts.setdefault(context_id, set())
            for paper in papers:
                key = _paper_dedupe_key(paper)
                if key:
                    seen.add(key)


# ---------------------------------------------------------------------------
# search_paper_wiki
# ---------------------------------------------------------------------------

class SearchPaperWikiTool(AgentTool):
    """Scoped paper-wiki lookup over accumulated judged literature."""

    name = "search_paper_wiki"
    description = (
        "Search accumulated paper memory for role- and intent-scoped canonical paper "
        "summaries. Use this before fresh retrieval when prior sessions may already "
        "cover the intent."
    )
    parameters = {
        "type": "object",
        "properties": {
            "background": {"type": "string", "description": "User question plus relevant dataset summary/context."},
            "requirements": {
                "type": "string",
                "description": "Current research-plan constraints to rank retrieved summaries against.",
            },
            "retrieval_goal": {
                "type": "string",
                "enum": [
                    "method_selection",
                    "evidence_pattern",
                    "prior_findings",
                    "contradiction",
                    "validation",
                    "extension_opportunity",
                    "broad_background",
                ],
            },
            "retrieval_intent": {"type": "string", "description": "Specific literature question."},
            "top_k": {"type": "integer", "description": "Default 5, maximum 10."},
        },
        "required": ["retrieval_goal", "retrieval_intent", "requirements", "background"],
        "additionalProperties": False,
    }

    def __init__(self, *, role: str):
        self._role = role.lower().strip()

    def run(
        self,
        *,
        background: str,
        requirements: str,
        retrieval_goal: str,
        retrieval_intent: str,
        top_k: int = 5,
        **_: Any,
    ) -> dict[str, Any]:
        limit = _clamped_int(top_k, default=5, lower=1, upper=10)
        papers = _query_paper_wiki_compact(
            role=self._role,
            user_question=background,
            data_summary=requirements,
            retrieval_goal=_normalize_retrieval_goal(retrieval_goal),
            retrieval_intent=retrieval_intent,
            top_k=limit,
        )
        papers = _deduplicate_papers(papers)
        return {
            "retrieval_intent": retrieval_intent,
            "retrieval_goal": _normalize_retrieval_goal(retrieval_goal),
            "papers": papers,
            "sufficient_memory": bool(papers),
            "message": "" if papers else "No scoped paper wiki entries found. Fresh retrieval may be needed.",
        }


# ---------------------------------------------------------------------------
# fetch_paper_wiki
# ---------------------------------------------------------------------------

class FetchPaperWikiTool(AgentTool):
    """Return the curated wiki summary for a known paper."""

    name = "fetch_paper_wiki"
    description = (
        "Fetch the curated paper wiki summary for a known paper_id. Use this before "
        "fetch_paper_content when a paper detail is needed."
    )
    parameters = {
        "type": "object",
        "properties": {
            "paper_id": {
                "type": "string",
                "description": "The paper_id from search_paper_wiki or retrieve_literature.",
            },
        },
        "required": ["paper_id"],
        "additionalProperties": False,
    }

    def run(self, *, paper_id: str, **_: Any) -> dict[str, Any]:
        paper = _get_wiki_paper(paper_id)
        if paper is None:
            return {
                "paper_id": paper_id,
                "content_status": "not_found",
                "error": f"Paper '{paper_id}' not found in wiki.",
            }
        return _paper_wiki_summary(paper)


# ---------------------------------------------------------------------------
# traverse_paper_wiki
# ---------------------------------------------------------------------------

class TraversePaperWikiTool(AgentTool):
    """Return papers already indexed in the paper wiki for a given task.

    Use this after retrieve_literature to find related papers the system has
    already processed in prior sessions — without repeating keyword search.
    The wiki grows over time: more sessions means richer coverage.
    """

    name = "traverse_paper_wiki"
    description = (
        "Retrieve papers from the paper knowledge wiki for a given task. "
        "The wiki contains papers retrieved and indexed in prior sessions — "
        "use this alongside retrieve_literature to access accumulated knowledge "
        "without re-running keyword search. "
        "Returns paper summaries including: questions answered, key findings, "
        "boundary conditions, and which papers they extend."
    )
    parameters = {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": (
                    "The tool wiki task ID to look up papers for. "
                    "Examples: 'rna_cell_type_annotation', 'rna_batch_correction', "
                    "'rna_clustering', 'rna_differential_expression'. "
                    "Use wiki_query_tasks to see available task IDs if unsure."
                ),
            },
        },
        "required": ["task_id"],
        "additionalProperties": False,
    }

    def run(self, *, task_id: str, **_: Any) -> list[dict[str, Any]]:
        index = get_paper_index()
        papers = index.get_papers_for_task(task_id)
        if not papers:
            return [{"message": f"No papers indexed yet for task '{task_id}'. Use retrieve_literature first."}]
        # Return compact view — content can be large
        return [_compact_paper(p) for p in papers]


# ---------------------------------------------------------------------------
# get_related_papers
# ---------------------------------------------------------------------------

class GetRelatedPapersTool(AgentTool):
    """Follow extends edges from a paper to find what it builds on.

    Use this for depth retrieval: once you have a key paper, find the
    foundational papers it extends and the papers that have extended it.
    Traverses up to 2 hops.
    """

    name = "get_related_papers"
    description = (
        "Follow extends edges from a paper in the wiki to find related papers. "
        "Returns papers the given paper builds on (extends chain, up to 2 hops) "
        "and papers that build on it (reverse extends). "
        "Use this for depth retrieval after finding a key paper via traverse_paper_wiki "
        "or retrieve_literature. paper_id must be a wiki paper_id (from traverse_paper_wiki results)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "paper_id": {
                "type": "string",
                "description": "The wiki paper_id to traverse from (from traverse_paper_wiki results).",
            },
        },
        "required": ["paper_id"],
        "additionalProperties": False,
    }

    def run(self, *, paper_id: str, **_: Any) -> dict[str, Any]:
        index = get_paper_index()
        paper = index.get_paper(paper_id)
        if paper is None:
            return {"error": f"Paper '{paper_id}' not found in wiki. Use traverse_paper_wiki first."}

        extends_chain = index.get_extends_chain(paper_id, max_depth=2)
        extended_by = index.get_papers_extending(paper_id)

        return {
            "paper": _compact_paper(paper),
            "extends": [_compact_paper(p) for p in extends_chain],
            "extended_by": [_compact_paper(p) for p in extended_by],
        }


# ---------------------------------------------------------------------------
# fetch_paper_content
# ---------------------------------------------------------------------------

class FetchPaperContentTool(AgentTool):
    """Drill into a specific section of a retrieved paper."""

    name = "fetch_paper_content"
    description = (
        "Read section-level or query-targeted detailed content from a known paper. "
        "Use fetch_paper_wiki first; call this only when the curated wiki summary "
        "is not detailed enough."
    )
    parameters = {
        "type": "object",
        "properties": {
            "paper_id": {
                "type": "string",
                "description": "The paper_id, doc_id, or vector_doc_id from search/retrieval results.",
            },
            "section": {
                "type": "string",
                "description": "Optional section to read, e.g. methods, results, analysis, figure_captions, benchmark_methods, metrics_used.",
            },
            "query": {
                "type": "string",
                "description": "Optional query to search within this known paper.",
            },
            "max_chars": {
                "type": "integer",
                "description": "Maximum characters to return. Default 4000, maximum 12000.",
            },
        },
        "required": ["paper_id"],
        "additionalProperties": False,
    }

    def __init__(self, *, retriever: LiteratureRetriever):
        self._retriever = retriever

    def run(
        self,
        *,
        paper_id: str,
        section: str | None = None,
        query: str | None = None,
        max_chars: int = 4000,
        content_need: str = "",
        section_type: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        section_name = str(section or section_type or "").strip().lower()
        query_text = str(query or content_need or "").strip()
        limit = _clamped_int(max_chars, default=4000, lower=500, upper=12000)
        if not section_name and not query_text:
            return {
                "paper_id": paper_id,
                "content_status": "not_found",
                "error": "fetch_paper_content requires at least one of section or query.",
            }

        if section_name:
            fresh = self._retriever.fetch_paper_section(paper_id, section_name)
            if not fresh.get("error"):
                fresh["query"] = query_text
                fresh["section"] = section_name
                fresh["source"] = "fresh_retrieval"
                _truncate_content_fields(fresh, limit)
                return fresh

        wiki_content = _fetch_paper_wiki_section(
            paper_id=paper_id,
            section=section_name,
            query=query_text,
            max_chars=limit,
        )
        if wiki_content:
            return wiki_content

        if query_text:
            fresh = self._retriever.fetch_paper_section(paper_id, "abstract")
            if not fresh.get("error"):
                fresh["query"] = query_text
                fresh["section"] = section_name or "abstract"
                fresh["source"] = "fresh_retrieval"
                _truncate_content_fields(fresh, limit)
                return fresh
        return {
            "error": f"Paper content not found for paper_id={paper_id}.",
            "paper_id": paper_id,
            "section": section_name,
            "query": query_text,
            "content_status": "not_found",
        }


# ---------------------------------------------------------------------------
# Registry builder
# ---------------------------------------------------------------------------

def build_panelist_tool_registry(
    *,
    role: str,
    retriever: LiteratureRetriever,
    judge: PaperJudge,
    paper_md_writer: Any | None = None,
) -> AgentToolRegistry:
    """Build the tool registry for a panelist agent.

    Args:
        role:            "biologist", "statistician", or "bioinformatician"
        retriever:       Shared LiteratureRetriever instance (one per panel run,
                         shared across panelists to share the RAGStore).
        judge:           PaperJudge instance (role-specific question is passed at
                         call time, so one instance can serve all roles).
        paper_md_writer: PaperMDWriter instance (optional). When provided, relevant
                         papers are written to the paper wiki after each retrieval.
    """
    registry = AgentToolRegistry()
    registry.register(SearchPaperWikiTool(role=role))
    registry.register(RetrieveLiteratureTool(
        retriever=retriever,
        judge=judge,
        role=role,
        paper_md_writer=paper_md_writer,
    ))
    registry.register(FetchPaperWikiTool())
    registry.register(FetchPaperContentTool(retriever=retriever))
    return registry


def build_paper_detail_tool_registry(*, retriever: LiteratureRetriever) -> AgentToolRegistry:
    """Build paper detail lookup tools for Mediator/Adversary/Analyzer agents."""
    registry = AgentToolRegistry()
    registry.register(FetchPaperWikiTool())
    registry.register(FetchPaperContentTool(retriever=retriever))
    return registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compact_paper(paper: dict[str, Any]) -> dict[str, Any]:
    """Return a compact view of a paper node for tool output."""
    content = str(paper.get("content") or "")
    sections = _parse_md_sections(content)
    available_sections = sorted(sections.keys())
    analysis = _section(sections, "analysis", "methods_used", "method_and_dataset")
    findings = _section(sections, "key_findings", "main_findings")
    paper_sections = {
        "summary": _section(sections, "summary"),
        "background": _section(sections, "background", "summary"),
        "method_and_dataset": _section(sections, "method_and_dataset"),
        "analysis": analysis,
        "benchmark_methods": _section(sections, "benchmark_methods"),
        "key_findings": findings,
        "limitations": _section(sections, "limitations"),
        "metrics_used": _section(sections, "metrics_used"),
        "figure_captions": _section(sections, "figure_captions"),
    }

    return {
        "paper_id": paper.get("paper_id"),
        "title": paper.get("title"),
        "published": paper.get("published") or paper.get("added") or "",
        "source": "paper_wiki",
        "objective": paper_sections["summary"],
        "background": paper_sections["background"],
        "method_and_dataset": paper_sections["method_and_dataset"],
        "analysis": paper_sections["analysis"],
        "benchmark_methods": paper_sections["benchmark_methods"],
        "main_findings": paper_sections["key_findings"],
        "limitations": paper_sections["limitations"],
        "metrics_used": paper_sections["metrics_used"],
        "figure_captions": paper_sections["figure_captions"],
        "paper_sections": paper_sections,
        "available_sections": available_sections,
        "summary": paper_sections["summary"],
        "key_findings": findings,
        "relevant": True,
        "confidence": 1.0,
        "judge_relevance": True,
        "judge_confidence": 1.0,
        "retrieval_intent_fit": "direct",
        "usefulness": "prior_findings",
        "return_to_panelist": True,
        "persist_to_wiki": True,
        "missing_information": [],
        "reason": "Retrieved from accumulated paper wiki memory.",
    }


def _query_paper_wiki_compact(
    *,
    role: str,
    user_question: str,
    data_summary: str,
    retrieval_goal: str,
    retrieval_intent: str,
    top_k: int,
) -> list[dict[str, Any]]:
    index = get_paper_index()
    papers = index.query_papers(
        role=role,
        user_question=user_question,
        data_summary=data_summary,
        retrieval_goal=retrieval_goal,
        retrieval_intent=retrieval_intent,
        top_k=top_k,
    )
    return [_compact_paper(p) for p in papers]


def _canonicalize_judged_paper(
    paper: dict[str, Any],
    *,
    retrieval_intent: str,
    retrieval_goal: str,
    requirements: str,
    source: str,
) -> dict[str, Any]:
    confidence = float(paper.get("confidence", paper.get("judge_confidence", 0.0)) or 0.0)
    full_text_status = str(paper.get("full_text_status") or "abstract_only").strip() or "abstract_only"
    if full_text_status == "abstract_only" and retrieval_goal != "broad_background":
        confidence = min(confidence, 0.70)
    relevant = bool(paper.get("relevant", paper.get("judge_relevance", False)))
    intent_fit = str(paper.get("retrieval_intent_fit") or "").strip()
    if intent_fit not in {"direct", "partial", "weak", "off_target"}:
        if not relevant:
            intent_fit = "off_target"
        elif confidence >= _PERSIST_TO_WIKI_THRESHOLD:
            intent_fit = "direct"
        elif confidence > 0:
            intent_fit = "partial"
        else:
            intent_fit = "weak"
    available_sections = paper.get("available_sections")
    if not isinstance(available_sections, list):
        available_sections = _available_sections_from_summary(paper)
    canonical = {
        "paper_id": paper.get("paper_id") or paper.get("doc_id"),
        "doc_id": paper.get("doc_id") or paper.get("paper_id"),
        "vector_doc_id": paper.get("vector_doc_id") or paper.get("doc_id") or paper.get("paper_id"),
        "title": paper.get("title", ""),
        "url": paper.get("url", ""),
        "doi": paper.get("doi", ""),
        "source_ids": paper.get("source_ids") if isinstance(paper.get("source_ids"), dict) else {},
        "published": paper.get("published", ""),
        "source": source,
        "full_text_status": full_text_status,
        "abstract": paper.get("abstract", ""),
        "objective": paper.get("objective", ""),
        "background": paper.get("background", ""),
        "method_and_dataset": paper.get("method_and_dataset", ""),
        "analysis": paper.get("analysis") or paper.get("key_methods", ""),
        "benchmark_methods": paper.get("benchmark_methods", ""),
        "main_findings": paper.get("main_findings", ""),
        "limitations": paper.get("limitations", ""),
        "metrics_used": paper.get("metrics_used", ""),
        "figure_captions": paper.get("figure_captions", ""),
        "paper_sections": _paper_sections_from_summary(paper),
        "available_sections": available_sections,
        "retrieval_goal": retrieval_goal,
        "retrieval_intent": retrieval_intent,
        "requirements": requirements,
        "judge_relevance": relevant,
        "judge_confidence": confidence,
        "relevant": relevant,
        "confidence": confidence,
        "retrieval_intent_fit": intent_fit,
        "usefulness": paper.get("usefulness") or retrieval_goal,
        "return_to_panelist": relevant and intent_fit in {"direct", "partial"},
        "reason_returned": paper.get("reason_returned") or paper.get("reason") or "",
        "evidence_contribution": paper.get("evidence_contribution") or "",
        "covered_evidence_patterns": paper.get("covered_evidence_patterns") or [],
        "evidence_pattern": paper.get("evidence_pattern") or {
            "covered_fields": paper.get("covered_evidence_patterns") or [],
            "contribution": paper.get("evidence_contribution") or "",
        },
        "missing_information": paper.get("missing_information") or paper.get("missing_evidence") or [],
        "missing_evidence": paper.get("missing_evidence") or paper.get("missing_information") or [],
        "persist_to_wiki": False,
        "persistence_reason": "",
        "reason_not_persisted": "",
    }
    canonical["persist_to_wiki"] = _should_persist_to_wiki(canonical)
    if canonical["persist_to_wiki"]:
        canonical["persistence_reason"] = "Relevant, confident, intent-fit paper with useful analysis summary."
    else:
        canonical["reason_not_persisted"] = "Below persistence threshold or lacks direct/partial fit/useful analysis."
    return canonical


def _available_sections_from_summary(paper: dict[str, Any]) -> list[str]:
    sections = ["abstract"] if paper.get("abstract") else []
    if paper.get("analysis") or paper.get("key_methods"):
        sections.append("methods")
    if paper.get("benchmark_methods"):
        sections.append("benchmark_methods")
    if paper.get("main_findings"):
        sections.append("results")
    if paper.get("limitations"):
        sections.append("discussion")
    if paper.get("figure_captions"):
        sections.append("figure_captions")
    return sections


def _paper_sections_from_summary(paper: dict[str, Any]) -> dict[str, str]:
    return {
        "summary": str(paper.get("objective") or paper.get("summary") or "").strip(),
        "background": str(paper.get("background") or "").strip(),
        "method_and_dataset": str(paper.get("method_and_dataset") or "").strip(),
        "analysis": str(paper.get("analysis") or paper.get("key_methods") or "").strip(),
        "benchmark_methods": str(paper.get("benchmark_methods") or "").strip(),
        "key_findings": str(paper.get("main_findings") or paper.get("key_findings") or "").strip(),
        "limitations": str(paper.get("limitations") or "").strip(),
        "metrics_used": str(paper.get("metrics_used") or "").strip(),
        "figure_captions": str(paper.get("figure_captions") or "").strip(),
    }


def _should_return_to_panelist(paper: dict[str, Any]) -> bool:
    intent_fit = str(paper.get("retrieval_intent_fit") or paper.get("intent_fit") or "").strip()
    return bool(paper.get("relevant", paper.get("judge_relevance", False))) and intent_fit in {"direct", "partial"}


def _should_persist_to_wiki(paper: dict[str, Any]) -> bool:
    intent_fit = str(paper.get("retrieval_intent_fit") or "").strip()
    return (
        bool(paper.get("relevant", paper.get("judge_relevance", False)))
        and float(paper.get("confidence", paper.get("judge_confidence", 0.0)) or 0.0) >= _PERSIST_TO_WIKI_THRESHOLD
        and intent_fit == "direct"
        and bool(str(paper.get("analysis") or paper.get("key_methods") or "").strip())
    )


def _join_context(*, background: str, requirements: str) -> str:
    requirements = str(requirements or "").strip()
    background = str(background or "").strip()
    if not requirements:
        return background
    return f"{background}\n\nREQUIREMENTS FOR JUDGING/RERANKING:\n{requirements}"


def _exclude_keys(exclude_ids: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    field_map = {
        "paper_ids": "paper_id",
        "dois": "doi",
        "pmids": "pmid",
        "pmcids": "pmcid",
        "semantic_scholar_ids": "semantic_scholar_id",
        "openalex_ids": "openalex_id",
        "normalized_titles": "normalized_title",
    }
    for raw_key, mapped in field_map.items():
        values = exclude_ids.get(raw_key, [])
        if isinstance(values, str):
            values = [values]
        if not isinstance(values, list):
            continue
        for value in values:
            text = str(value or "").strip().lower()
            if not text:
                continue
            if mapped == "normalized_title":
                keys.add(f"title:{_normalize_title(text)}")
            else:
                keys.add(text)
    return keys


def _get_wiki_paper(paper_id: str) -> dict[str, Any] | None:
    index = get_paper_index()
    return index.get_paper(paper_id)


def _paper_wiki_summary(paper: dict[str, Any]) -> dict[str, Any]:
    sections = _parse_md_sections(str(paper.get("content") or ""))
    paper_sections = {
        "summary": _section(sections, "summary"),
        "background": _section(sections, "background", "summary"),
        "method_and_dataset": _section(sections, "method_and_dataset"),
        "analysis": _section(sections, "analysis", "methods_used"),
        "benchmark_methods": _section(sections, "benchmark_methods"),
        "key_findings": _section(sections, "key_findings"),
        "limitations": _section(sections, "limitations"),
        "metrics_used": _section(sections, "metrics_used"),
        "figure_captions": _section(sections, "figure_captions"),
    }
    return {
        "paper_id": paper.get("paper_id"),
        "title": paper.get("title", ""),
        "content_status": "found",
        "source": "paper_wiki",
        "summary": paper_sections["summary"],
        "background": paper_sections["background"],
        "method_and_dataset": paper_sections["method_and_dataset"],
        "analysis": paper_sections["analysis"],
        "benchmark_methods": paper_sections["benchmark_methods"],
        "key_findings": paper_sections["key_findings"],
        "limitations": paper_sections["limitations"],
        "metrics_used": paper_sections["metrics_used"],
        "figure_captions": paper_sections["figure_captions"],
        "paper_sections": paper_sections,
        "available_sections": sorted(sections.keys()),
    }


def _fetch_paper_wiki_section(
    *,
    paper_id: str,
    section: str,
    query: str,
    max_chars: int,
) -> dict[str, Any] | None:
    paper = _get_wiki_paper(paper_id)
    if paper is None:
        return None
    sections = _parse_md_sections(str(paper.get("content") or ""))
    key = str(section or "").strip().lower().replace(" ", "_")
    if key:
        text = sections.get(key, "")
        heading = key
    else:
        text, heading = _search_sections(sections, query=query)
    if not text:
        return None
    return {
        "paper_id": paper_id,
        "title": paper.get("title", ""),
        "section": key,
        "section_heading": heading,
        "query": query,
        "content": text[:max_chars],
        "text": text[:max_chars],
        "content_status": "found" if len(text) <= max_chars else "partial",
        "source": "paper_wiki",
        "available_sections": sorted(sections.keys()),
    }


def _search_sections(sections: dict[str, str], *, query: str) -> tuple[str, str]:
    if not sections:
        return "", ""
    query_terms = {t for t in re.findall(r"[a-z0-9]+", str(query or "").lower()) if len(t) > 2}
    if not query_terms:
        text = "\n\n".join(f"## {name}\n{body}" for name, body in sections.items())
        return text, "all_available_sections"
    scored: list[tuple[int, str, str]] = []
    for name, body in sections.items():
        haystack = f"{name} {body}".lower()
        score = sum(1 for term in query_terms if term in haystack)
        if score:
            scored.append((score, name, body))
    if not scored:
        return "", ""
    scored.sort(reverse=True)
    chunks = [f"## {name}\n{body}" for _, name, body in scored[:3]]
    return "\n\n".join(chunks), scored[0][1]


def _parse_md_sections(content: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_heading = ""
    current_lines: list[str] = []
    for line in str(content or "").splitlines():
        if line.startswith("## "):
            if current_heading:
                sections[current_heading] = "\n".join(current_lines).strip()
            current_heading = line[3:].strip().lower().replace(" ", "_")
            current_lines = []
        else:
            current_lines.append(line)
    if current_heading:
        sections[current_heading] = "\n".join(current_lines).strip()
    return sections


def _section(sections: dict[str, str], *names: str) -> str:
    for name in names:
        key = str(name or "").strip().lower().replace(" ", "_")
        if sections.get(key):
            return sections[key]
    return ""


def _truncate_content_fields(payload: dict[str, Any], max_chars: int) -> None:
    for key in ("content", "text"):
        if isinstance(payload.get(key), str) and len(payload[key]) > max_chars:
            payload[key] = payload[key][:max_chars]
            payload["content_status"] = "partial"


def _normalize_retrieval_goal(value: str | None) -> str:
    valid = {
        "method_selection",
        "evidence_pattern",
        "prior_findings",
        "contradiction",
        "validation",
        "extension_opportunity",
        "broad_background",
    }
    goal = str(value or "").strip().lower()
    return goal if goal in valid else "prior_findings"


def _deduplicate_papers(papers: list[dict[str, Any]], *, use_title_fallback: bool = False) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for paper in papers:
        key = _paper_dedupe_key(paper, use_title_fallback=use_title_fallback)
        if not key:
            key = f"unknown:{len(order)}"
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = dict(paper)
            order.append(key)
            continue
        by_key[key] = _merge_duplicate(existing, paper)
    return [by_key[key] for key in order]


def _paper_dedupe_key(paper: dict[str, Any], *, use_title_fallback: bool = False) -> str:
    source_ids = paper.get("source_ids") if isinstance(paper.get("source_ids"), dict) else {}
    title = _normalize_title(str(paper.get("title") or ""))
    if use_title_fallback and title:
        return f"title:{title}"
    candidates = [
        paper.get("doi"),
        source_ids.get("doi"),
        source_ids.get("pmid"),
        source_ids.get("pmcid"),
        source_ids.get("semantic_scholar_id"),
        source_ids.get("openalex_id"),
        paper.get("doc_id"),
        paper.get("paper_id"),
    ]
    for item in candidates:
        value = str(item or "").strip().lower()
        if value:
            return value
    return f"title:{title}" if title or use_title_fallback else ""


def _normalize_title(title: str) -> str:
    text = str(title or "").lower()
    text = re.sub(r"[\W_]+", " ", text)
    text = re.sub(r"\b(preprint|published|version|revised)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _merge_duplicate(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_status = str(left.get("full_text_status") or "abstract_only")
    right_status = str(right.get("full_text_status") or "abstract_only")
    status_rank = {"pmc_xml": 4, "preprint_jats": 3, "open_pdf": 2, "abstract_only": 1, "": 0}
    left_conf = float(left.get("confidence", left.get("judge_confidence", 0.0)) or 0.0)
    right_conf = float(right.get("confidence", right.get("judge_confidence", 0.0)) or 0.0)
    left_score = (status_rank.get(left_status, 0), left_conf)
    right_score = (status_rank.get(right_status, 0), right_conf)
    primary, secondary = (right, left) if right_score > left_score else (left, right)
    merged = dict(primary)
    for key in ("source_ids",):
        values: dict[str, Any] = {}
        if isinstance(secondary.get(key), dict):
            values.update(secondary[key])
        if isinstance(primary.get(key), dict):
            values.update(primary[key])
        if values:
            merged[key] = values
    for key in ("retrieval_intents", "retrieval_goals"):
        items: list[str] = []
        for payload in (secondary.get(key), primary.get(key), secondary.get(key[:-1]), primary.get(key[:-1])):
            if isinstance(payload, list):
                items.extend(str(x) for x in payload if str(x).strip())
            elif isinstance(payload, str) and payload.strip():
                items.append(payload.strip())
        if items:
            merged[key] = list(dict.fromkeys(items))
    return merged
