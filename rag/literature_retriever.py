"""Standalone literature retriever for the Scientist panel.

Designed for panelist agents — takes a free-form base_query and background,
runs the full retrieval pipeline, and returns paper summaries ready for
PaperJudge and panelist reasoning.

Unlike ConsultantRAGAgent (which requires a Config object and textgrad engine),
this class:
- Takes base_query and background as plain strings
- Uses the OpenAI client for LLM calls (consistent with agent infrastructure)
- Reuses RAGStore for embedding/search
- Reuses fetch_* functions from rag.sources
- Runs PaperJudge automatically after retrieval

Typical usage (inside a panelist tool):
    retriever = LiteratureRetriever(
        rag_store=store,
        engine_name="gpt-4o-mini",
        client=client,
    )
    papers = retriever.retrieve(
        base_query="CD4 CD8 T cell marker programs IBD PBMC",
        background="8432 PBMC cells, IBD vs healthy, donor_id batch",
        role="biologist",
        question="What cell types are known in IBD PBMC?",
        top_k=8,
    )
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from prompts.literature_prompts import (
    LITERATURE_SUMMARY_SYSTEM as _SUMMARY_SYSTEM,
    LITERATURE_SUMMARY_PROMPT as _SUMMARY_PROMPT,
)
from rag.store_backend import RAGStore
from rag.sources import (
    fetch_pubmed_documents,
    fetch_semantic_scholar_documents,
    fetch_openalex_documents,
    fetch_biorxiv_documents,
    fetch_core_document,
    fetch_open_pdf_core_document,
)
from rag.types import RAGDocument

logger = logging.getLogger(__name__)

MAX_RESULTS_PER_QUERY = 20
MAX_PMC_CANDIDATES = 40
DEFAULT_N_KEYWORD_QUERIES = 5
DEFAULT_N_SUBQUERIES = 4
DEFAULT_TOP_K = 8
DEFAULT_SEARCH_HITS = 20
DEFAULT_RRF_K = 60
# Bounds the HyDE-abstract cache (see LiteratureRetriever._hyde_cache) so it
# cannot grow unbounded across a long-lived (process-lifetime) retriever
# instance. Oldest entries are evicted FIFO once this cap is exceeded.
_MAX_HYDE_CACHE_ENTRIES = 512

# ---------------------------------------------------------------------------
# Prompts (OpenAI client style — no textgrad)
# ---------------------------------------------------------------------------

_KEYWORD_SYSTEM = (
    "You are a scientific literature search expert. Return only valid JSON."
)

_KEYWORD_PROMPT = """Generate search queries to retrieve papers relevant to the retrieval intent.

BACKGROUND:
{background}

RETRIEVAL_GOAL:
{retrieval_goal}

RETRIEVAL_INTENT:
{retrieval_intent}

BASE_QUERY:
{base_query}

Return ONLY a JSON object:
{{
  "pubmed_queries": ["PubMed Boolean query 1", "PubMed Boolean query 2", ...],
  "natural_queries": ["natural language query for semantic search 1", ...]
}}

Rules:
- pubmed_queries: 3-5 short, high-recall PubMed Boolean queries. No filters (pmc, review, english, dates).
- natural_queries: 3-5 natural language queries for semantic search APIs (Semantic Scholar, OpenAlex).
- Each query covers a distinct retrieval theme.
- Ground queries in the background, retrieval goal, retrieval intent, and base_query only.
"""

_SUBQUERY_SYSTEM = (
    "You are generating semantic retrieval subqueries for a biomedical RAG pipeline. "
    "Return only valid JSON."
)

_SUBQUERY_PROMPT = """Generate {n} independent subqueries and HyDE abstracts for vector search.

BACKGROUND:
{background}

RETRIEVAL_GOAL:
{retrieval_goal}

RETRIEVAL_INTENT:
{retrieval_intent}

BASE_QUERY:
{base_query}

Return ONLY a JSON object:
{{
  "items": [
    {{
      "subquery": "<short retrieval-friendly subquery>",
      "hyde_abstract": "<concise hypothetical scientific abstract>"
    }}
  ]
}}

Requirements:
- Subqueries must be non-overlapping and complementary.
- Use terminology authors actually use in paper titles and abstracts.
- HyDE abstracts should be written as if they are real paper abstracts.
- Do not invent citations, authors, or journal names.
"""


# ---------------------------------------------------------------------------
# LiteratureRetriever
# ---------------------------------------------------------------------------

class LiteratureRetriever:
    """Full retrieval pipeline for panelist agents.

    Args:
        rag_store:   RAGStore instance (shared across panelists).
        engine_name: Model for keyword/subquery generation + paper summaries.
        client:      OpenAI-compatible client.
        cache_dir:   Optional directory for caching fetched documents.
    """

    def __init__(
        self,
        *,
        rag_store: RAGStore,
        engine_name: str,
        client: Any,
        cache_dir: Path | None = None,
    ):
        self.store = rag_store
        self.engine_name = engine_name
        self.client = client
        self.cache_dir = Path(cache_dir) if cache_dir else rag_store.root_dir / "panelist_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._paper_documents_by_id: dict[str, RAGDocument] = {}

        # HyDE-abstract cache. Keyed on the normalized subquery text (the
        # base_query a panelist issues to retrieve_literature — see
        # RetrieveLiteratureTool.run in agents/panelist_tools.py), this
        # avoids redundantly regenerating HyDE abstracts (_generate_subqueries,
        # an LLM call) when the three panelists (biologist/statistician/
        # bioinformatician) share this retriever instance and issue
        # overlapping subqueries. Panelists run concurrently in a
        # ThreadPoolExecutor (agents/scientist_panel.py::_run_parallel), so
        # this retriever instance -- and this cache -- is accessed from
        # multiple threads at once; _cache_lock guards all reads/writes.
        #
        # IMPORTANT — what is (and is NOT) cached:
        # Only the HyDE subquery/abstract *generation* result is cached here.
        # `_generate_subqueries` is a pure function of (base_query,
        # retrieval_intent, retrieval_goal, background, n) — it does not
        # depend on the document index, on `role`, or on which research
        # phase/question is in flight, so reusing it is always safe: two
        # calls with the same normalized base_query always deserve the same
        # HyDE abstracts, regardless of phase.
        #
        # Search results (`_rrf_search` / `store.search_runtime`) are
        # deliberately NEVER cached. Each `retrieve()` call fetches its own
        # fresh document set and builds/searches its own vector index
        # (`_collection_name` is unique per role+base_query), so a cached
        # ranked-document list could reference documents from a completely
        # different research phase/question — that would be a real staleness
        # bug (a prior question's results silently returned instead of the
        # current one's), not a performance optimization. Search is also the
        # cheap part of this pipeline; the LLM call is what's worth avoiding.
        #
        # Because this cache is a pure function of query text, it is safe for
        # the lifetime of the process — no phase-boundary reset is required
        # for correctness. `reset_cache()` remains available (e.g. for tests,
        # or if a caller wants to bound memory more eagerly), and the cache
        # is also bounded by `_MAX_HYDE_CACHE_ENTRIES` with FIFO eviction so
        # it cannot grow unbounded across a long-lived process.
        self._hyde_cache: "OrderedDict[str, list[dict[str, str]]]" = OrderedDict()
        self._cache_lock = threading.Lock()

    def reset_cache(self) -> None:
        """Clear the cached HyDE abstracts.

        Not required for correctness (see the cache-safety note in
        `__init__`) since HyDE generation is a pure function of query text.
        Provided for tests and for callers that want to bound memory more
        eagerly than the built-in FIFO cap.
        """
        with self._cache_lock:
            self._hyde_cache.clear()

    def retrieve(
        self,
        *,
        retrieval_intent: str | None = None,
        retrieval_goal: str | None = None,
        base_query: str | None = None,
        background: str,
        role: str,
        question: str | None = None,
        top_k: int = DEFAULT_TOP_K,
        n_keyword_queries: int = DEFAULT_N_KEYWORD_QUERIES,
        n_subqueries: int = DEFAULT_N_SUBQUERIES,
    ) -> list[dict[str, Any]]:
        """Run the full pipeline and return labeled top-K paper summaries.

        Steps:
        1. Generate keyword queries (PubMed + natural language)
        2. Fetch from PubMed + S2 + OpenAlex in parallel
        3. Generate HyDE subqueries
        4. Build vector index → search → RRF → top_k
        5. Generate paper summaries
        6. PaperJudge (caller handles this — we return summaries with doc_id)

        Returns list of paper summary dicts ready for PaperJudge.
        """
        retrieval_intent = (retrieval_intent or question or base_query or "").strip()
        retrieval_goal = _normalize_retrieval_goal(retrieval_goal)
        base_query = (base_query or retrieval_intent).strip()
        background = background.strip()

        # Step 1: generate queries
        query_plan = self._generate_queries(
            base_query=base_query,
            retrieval_intent=retrieval_intent,
            retrieval_goal=retrieval_goal,
            background=background,
            n=n_keyword_queries,
        )
        pubmed_queries = query_plan["pubmed_queries"]
        natural_queries = query_plan["natural_queries"]

        # Step 2: fetch documents in parallel from all three sources
        documents = self._fetch_documents(
            pubmed_queries=pubmed_queries,
            natural_queries=natural_queries,
            base_query=base_query,
        )
        if not documents:
            return []

        # Step 3: generate HyDE subqueries — cached by normalized base_query.
        #
        # This retriever is shared across the three panelists, and the same
        # (or an overlapping) base_query is frequently re-issued within a
        # research phase. HyDE generation is a pure function of query text
        # (see the cache-safety note in __init__), so on a cache hit we skip
        # the _generate_subqueries LLM call and reuse the cached abstracts.
        cache_key = _normalize_subquery(base_query)
        with self._cache_lock:
            subquery_items = self._hyde_cache.get(cache_key)
        if subquery_items is None:
            subquery_items = self._generate_subqueries(
                base_query=base_query,
                retrieval_intent=retrieval_intent,
                retrieval_goal=retrieval_goal,
                background=background,
                n=n_subqueries,
            )
            with self._cache_lock:
                self._hyde_cache[cache_key] = subquery_items
                while len(self._hyde_cache) > _MAX_HYDE_CACHE_ENTRIES:
                    self._hyde_cache.popitem(last=False)

        # Step 4: build index, search, RRF — always fresh, never cached.
        # Each retrieve() call has its own freshly fetched document set and
        # its own vector collection (_collection_name is unique per
        # role+base_query); reusing a prior search result here would risk
        # returning a different research phase/question's papers instead of
        # the current call's freshly fetched ones.
        collection_name = self._collection_name(base_query, role)
        self.store.build_runtime_index(collection_name, documents, rebuild=True)
        documents_by_id = {doc.doc_id: doc for doc in documents}

        ranked = self._rrf_search(
            collection_name=collection_name,
            subquery_items=subquery_items,
            documents_by_id=documents_by_id,
            top_k=top_k,
        )

        # Step 5: generate summaries
        summaries = []
        for doc in ranked:
            summary = self._summarize_document(doc)
            summaries.append({
                "doc_id": doc.doc_id,
                "title": doc.title,
                "published": doc.published,
                "url": doc.url,
                "source": doc.source,
                "doi": doc.doi,
                "source_ids": _source_ids(doc),
                "full_text_status": _full_text_status(doc),
                "pdf_url": str(doc.metadata.get("pdf_url") or ""),
                "pdf_parser": str(doc.metadata.get("pdf_parser") or ""),
                "section_recovery_status": str(doc.metadata.get("section_recovery_status") or ""),
                "retrieval_goal": retrieval_goal,
                "retrieval_intent": retrieval_intent,
                "base_query": base_query,
                "abstract": doc.abstract,
                **summary,
            })

        return summaries

    # ------------------------------------------------------------------
    # Step 1: query generation
    # ------------------------------------------------------------------

    def _generate_queries(
        self,
        *,
        base_query: str,
        retrieval_intent: str,
        retrieval_goal: str,
        background: str,
        n: int,
        max_attempts: int = 3,
    ) -> dict[str, list[str]]:
        prompt = _KEYWORD_PROMPT.format(
            background=background[:3000],
            retrieval_goal=retrieval_goal,
            retrieval_intent=retrieval_intent,
            base_query=base_query,
        )
        for attempt in range(max_attempts):
            try:
                text = self._llm(prompt, system=_KEYWORD_SYSTEM)
                payload = _extract_json(text)
                pubmed = [
                    str(q).strip() for q in payload.get("pubmed_queries", [])
                    if str(q).strip()
                ][:n]
                natural = [
                    str(q).strip() for q in payload.get("natural_queries", [])
                    if str(q).strip()
                ][:n]
                if pubmed or natural:
                    return {"pubmed_queries": pubmed, "natural_queries": natural}
            except Exception as exc:
                logger.warning("Query generation attempt %d failed: %s", attempt + 1, exc)
        # Fallback: use base_query directly
        return {"pubmed_queries": [base_query], "natural_queries": [base_query]}

    # ------------------------------------------------------------------
    # Step 2: multi-source fetch
    # ------------------------------------------------------------------

    def _fetch_documents(
        self,
        *,
        pubmed_queries: list[str],
        natural_queries: list[str],
        base_query: str,
    ) -> list[RAGDocument]:
        all_queries = list(dict.fromkeys(pubmed_queries + natural_queries))

        with ThreadPoolExecutor(max_workers=4) as pool:
            f_pubmed = pool.submit(fetch_pubmed_documents, pubmed_queries, MAX_RESULTS_PER_QUERY)
            f_s2 = pool.submit(fetch_semantic_scholar_documents, all_queries, MAX_RESULTS_PER_QUERY)
            f_oa = pool.submit(fetch_openalex_documents, natural_queries, MAX_RESULTS_PER_QUERY)
            f_preprints = pool.submit(self._fetch_preprints, natural_queries or all_queries or [base_query])
            try:
                pubmed_docs = f_pubmed.result()
            except Exception as exc:
                logger.warning("PubMed fetch failed: %s", exc)
                pubmed_docs = []
            try:
                s2_docs = f_s2.result()
            except Exception as exc:
                logger.warning("Semantic Scholar fetch failed: %s", exc)
                s2_docs = []
            try:
                oa_docs = f_oa.result()
            except Exception as exc:
                logger.warning("OpenAlex fetch failed: %s", exc)
                oa_docs = []
            try:
                preprint_docs = f_preprints.result()
            except Exception as exc:
                logger.warning("bioRxiv/medRxiv fetch failed: %s", exc)
                preprint_docs = []

        candidates = _deduplicate_documents(pubmed_docs + s2_docs + oa_docs + preprint_docs)
        candidates = candidates[:MAX_PMC_CANDIDATES]

        # Try structured full text first, then lower-quality open PDF fallback.
        enriched: list[RAGDocument] = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            future_map = {pool.submit(self._resolve_document, doc): doc for doc in candidates}
            for future in as_completed(future_map):
                result = future.result()
                if result is not None:
                    enriched.append(result)

        enriched = _deduplicate_documents(enriched)
        enriched.sort(key=lambda d: (str(d.published or ""), d.title), reverse=True)

        for doc in enriched:
            self._paper_documents_by_id[doc.doc_id] = doc

        return enriched

    def _resolve_document(self, doc: RAGDocument) -> RAGDocument | None:
        # Check cache
        cached = self.store.load_cached_core_document(doc.doc_id)
        if cached is not None and cached.doc_type == "core_full_text" and cached.sections:
            return cached
        # Try PMC full-text by PMID/PMCID, including IDs discovered via S2.
        pmid = str(doc.metadata.get("pmid") or "").strip()
        pmc_source = doc
        if doc.source != "pubmed" and pmid:
            pmc_source = RAGDocument(
                doc_id=f"pubmed:{pmid}",
                source="pubmed",
                source_id=pmid,
                title=doc.title,
                text=doc.text,
                abstract=doc.abstract,
                url=doc.url,
                authors=doc.authors,
                published=doc.published,
                doi=doc.doi,
                doc_type=doc.doc_type,
                categories=list(doc.categories),
                metadata=dict(doc.metadata),
            )
        if pmc_source.source == "pubmed":
            try:
                result = fetch_core_document(pmc_source)
                if result is not None and result.has_full_text:
                    core = result.document
                    self.store.save_cached_core_document(doc.doc_id, core)
                    return core
            except Exception as exc:
                logger.debug("PMC resolution failed for %s: %s", doc.doc_id, exc)
        # Try preprint JATS XML for bioRxiv/medRxiv.
        if doc.source in {"biorxiv", "medrxiv"}:
            try:
                result = fetch_core_document(doc)
                if result is not None and result.has_full_text:
                    core = result.document
                    self.store.save_cached_core_document(doc.doc_id, core)
                    return core
            except Exception as exc:
                logger.debug("Preprint JATS resolution failed for %s: %s", doc.doc_id, exc)

        # Try open-access PDF from Semantic Scholar/OpenAlex.
        try:
            result = fetch_open_pdf_core_document(doc)
            if result is not None and result.has_full_text:
                core = result.document
                self.store.save_cached_core_document(doc.doc_id, core)
                return core
        except Exception as exc:
            logger.debug("Open PDF resolution failed for %s: %s", doc.doc_id, exc)

        # Keep abstract-only docs.
        if doc.abstract:
            doc.metadata.setdefault("full_text_status", "abstract_only")
            return doc
        return None

    def _fetch_preprints(self, queries: list[str]) -> list[RAGDocument]:
        """Fetch a small recent preprint pool and filter it by query-token overlap."""
        try:
            docs = fetch_biorxiv_documents(days=365 * 5, max_papers=200)
        except Exception:
            return []
        query_tokens = _important_tokens(" ".join(queries))
        if not query_tokens:
            return docs[:MAX_RESULTS_PER_QUERY]
        ranked: list[tuple[int, RAGDocument]] = []
        for doc in docs:
            haystack = _important_tokens(f"{doc.title} {doc.abstract}")
            overlap = len(query_tokens & haystack)
            if overlap > 0:
                ranked.append((overlap, doc))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in ranked[:MAX_RESULTS_PER_QUERY]]

    # ------------------------------------------------------------------
    # Step 3: HyDE subquery generation
    # ------------------------------------------------------------------

    def _generate_subqueries(
        self,
        *,
        base_query: str,
        retrieval_intent: str,
        retrieval_goal: str,
        background: str,
        n: int,
        max_attempts: int = 3,
    ) -> list[dict[str, str]]:
        prompt = _SUBQUERY_PROMPT.format(
            background=background[:3000],
            retrieval_goal=retrieval_goal,
            retrieval_intent=retrieval_intent,
            base_query=base_query,
            n=n,
        )
        for attempt in range(max_attempts):
            try:
                text = self._llm(prompt, system=_SUBQUERY_SYSTEM)
                payload = _extract_json(text)
                items = [
                    {"subquery": str(item["subquery"]).strip(),
                     "hyde_abstract": str(item["hyde_abstract"]).strip()}
                    for item in payload.get("items", [])
                    if isinstance(item, dict)
                    and str(item.get("subquery", "")).strip()
                    and str(item.get("hyde_abstract", "")).strip()
                ]
                if items:
                    return items
            except Exception as exc:
                logger.warning("Subquery generation attempt %d failed: %s", attempt + 1, exc)
        return [{"subquery": base_query, "hyde_abstract": base_query}]

    # ------------------------------------------------------------------
    # Step 4: vector search + RRF
    # ------------------------------------------------------------------

    def _rrf_search(
        self,
        *,
        collection_name: str,
        subquery_items: list[dict[str, str]],
        documents_by_id: dict[str, RAGDocument],
        top_k: int,
    ) -> list[RAGDocument]:
        ranked_lists: list[list[tuple[str, float]]] = []
        for item in subquery_items:
            hits = self.store.search_runtime(
                collection_name, item["hyde_abstract"], n_results=DEFAULT_SEARCH_HITS
            )
            # search_runtime returns CHUNK-level hits, so the same doc_id can
            # appear at several consecutive ranks for multi-chunk (full-text)
            # documents. Collapse to one entry per doc_id, keeping the best
            # (lowest/first-seen) rank, before this list is fused with the
            # others -- otherwise heavily-chunked papers get several RRF
            # increments per subquery while abstract-only papers get one.
            ranked_lists.append(_collapse_to_best_rank_per_doc([(h.doc_id, h.score) for h in hits]))

        scores = rrf_fuse(ranked_lists, k=DEFAULT_RRF_K)

        ordered = sorted(scores.items(), key=lambda x: -x[1])
        result: list[RAGDocument] = []
        for doc_id, _ in ordered:
            doc = documents_by_id.get(doc_id)
            if doc is not None:
                result.append(doc)
            if len(result) >= top_k:
                break
        return result

    # ------------------------------------------------------------------
    # Step 5: paper summaries
    # ------------------------------------------------------------------

    def _summarize_document(self, doc: RAGDocument) -> dict[str, str]:
        # Check summary cache
        cache_path = self.cache_dir / f"summary_{doc.doc_id.replace(':', '_')}.json"
        if cache_path.exists():
            try:
                return json.loads(cache_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        section_map = {s.section_type: s.text for s in doc.sections}

        def _clip(text: str, n: int = 3500) -> str:
            return re.sub(r"\s+", " ", str(text or "")).strip()[:n]

        prompt = _SUMMARY_PROMPT.format(
            title=doc.title,
            published=doc.published or "unknown",
            abstract=_clip(doc.abstract, 2000),
            methods=_clip(section_map.get("methods", ""), 4500),
            results=_clip(section_map.get("results", ""), 3500),
            discussion=_clip(section_map.get("discussion", ""), 2500),
            figure_captions=_clip(section_map.get("figure_captions", ""), 3500),
        )
        try:
            text = self._llm(prompt, system=_SUMMARY_SYSTEM)
            payload = _extract_json(text)
            if isinstance(payload, dict):
                summary = {
                    "objective": str(payload.get("objective", "") or ""),
                    "background": str(payload.get("background", "") or ""),
                    "method_and_dataset": str(payload.get("method_and_dataset", "") or ""),
                    "analysis": str(payload.get("analysis", "") or payload.get("key_methods", "") or ""),
                    "benchmark_methods": str(payload.get("benchmark_methods", "") or ""),
                    "main_findings": str(payload.get("main_findings", "") or ""),
                    "limitations": str(payload.get("limitations", "") or ""),
                    "metrics_used": str(payload.get("metrics_used", "") or ""),
                    "figure_captions": str(payload.get("figure_captions", "") or ""),
                }
                # Backward-compatible alias for older wiki/paper-store code.
                summary["key_methods"] = summary["analysis"]
                cache_path.write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
                return summary
        except Exception as exc:
            logger.debug("Summary generation failed for %s: %s", doc.doc_id, exc)

        # Fallback: use abstract
        abstract_text = re.sub(r"\s+", " ", doc.abstract or "").strip()
        return {
            "objective": abstract_text,
            "background": "",
            "analysis": "",
            "key_methods": "",
            "main_findings": "",
            "limitations": "",
            "metrics_used": "",
            "figure_captions": "",
        }

    # ------------------------------------------------------------------
    # fetch_paper_section (exposed for panelist tool)
    # ------------------------------------------------------------------

    def fetch_paper_section(self, paper_id: str, section_type: str) -> dict[str, Any]:
        """Return a specific section of a retrieved paper."""
        doc = self._paper_documents_by_id.get(paper_id)
        if doc is None:
            return {"error": f"Unknown paper_id: {paper_id}. Call retrieve_literature first."}

        normalized = _normalize_section_type(section_type)
        for section in doc.sections:
            if section.section_type == normalized:
                return {
                    "paper_id": doc.doc_id,
                    "title": doc.title,
                    "section_type": section.section_type,
                    "section_heading": section.heading,
                    "text": section.text[:6000],
                }
        # Fallback: return abstract
        if normalized == "abstract" and doc.abstract:
            return {
                "paper_id": doc.doc_id,
                "title": doc.title,
                "section_type": "abstract",
                "section_heading": "Abstract",
                "text": doc.abstract,
            }
        available = [s.section_type for s in doc.sections]
        return {
            "error": f"Section '{section_type}' not found for paper_id={paper_id}.",
            "available_sections": available,
        }

    # ------------------------------------------------------------------
    # Internal LLM call
    # ------------------------------------------------------------------

    def _llm(self, user_prompt: str, *, system: str = "") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user_prompt})
        response = self.client.responses.create(
            model=self.engine_name,
            input=messages,
        )
        text = str(getattr(response, "output_text", "") or "").strip()
        if not text:
            for item in getattr(response, "output", []):
                content = getattr(item, "content", None)
                if isinstance(content, str):
                    return content.strip()
                elif isinstance(content, list):
                    for part in content:
                        t = getattr(part, "text", None)
                        if isinstance(t, str) and t.strip():
                            return t.strip()
        return text

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _collection_name(self, base_query: str, role: str) -> str:
        h = hashlib.sha256(f"{role}:{base_query}".encode()).hexdigest()[:12]
        return f"panelist_{role}_{h}"


def _collapse_to_best_rank_per_doc(
    ranked: list[tuple[str, float]],
) -> list[tuple[str, float]]:
    """Collapse a chunk-level ranked list to one entry per doc_id.

    ``ranked`` is a list of ``(doc_id, score)`` pairs already ordered best
    (lowest rank) first. When the same doc_id occurs more than once -- e.g. a
    full-text document contributing several chunk hits -- only its first
    (best-ranked) occurrence is kept.
    """
    seen: set[str] = set()
    collapsed: list[tuple[str, float]] = []
    for doc_id, score in ranked:
        if doc_id in seen:
            continue
        seen.add(doc_id)
        collapsed.append((doc_id, score))
    return collapsed


def rrf_fuse(
    ranked_lists: list[list[tuple[str, float]]],
    k: int = DEFAULT_RRF_K,
) -> dict[str, float]:
    """Reciprocal Rank Fusion over multiple ranked lists of ``(doc_id, score)``.

    Each inner list is first collapsed to one entry per doc_id (keeping the
    best/first-seen rank -- see :func:`_collapse_to_best_rank_per_doc`) so
    that a document occupying several consecutive positions in one list
    (e.g. multiple chunks of the same full-text paper) is not rewarded with
    multiple RRF increments relative to a document that appears once.

    Returns a mapping of doc_id -> fused RRF score, summed across lists.
    """
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, (doc_id, _) in enumerate(_collapse_to_best_rank_per_doc(ranked), start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return scores


def _normalize_subquery(text: str) -> str:
    """Normalize subquery/base_query text for per-phase cache-key comparison."""
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _extract_json(text: str) -> Any:
    cleaned = str(text or "").strip()
    match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group(1).strip()
    return json.loads(cleaned)


def _normalize_section_type(title: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(title or "").lower()).strip()
    if any(t in cleaned for t in ["abstract", "summary"]):
        return "abstract"
    if any(t in cleaned for t in ["method", "material", "approach"]):
        return "methods"
    if "result" in cleaned:
        return "results"
    if "discussion" in cleaned:
        return "discussion"
    if "conclusion" in cleaned:
        return "conclusion"
    if "introduction" in cleaned:
        return "introduction"
    return "supplement"


_VALID_RETRIEVAL_GOALS = {
    "method_selection",
    "evidence_pattern",
    "prior_findings",
    "contradiction",
    "validation",
    "extension_opportunity",
    "broad_background",
}


def _normalize_retrieval_goal(value: str | None) -> str:
    goal = str(value or "").strip().lower()
    return goal if goal in _VALID_RETRIEVAL_GOALS else "prior_findings"


def _full_text_status(doc: RAGDocument) -> str:
    status = str(doc.metadata.get("full_text_status") or "").strip()
    if status:
        return status
    if doc.doc_type == "core_full_text" and doc.source == "pmc":
        return "pmc_xml"
    if doc.doc_type == "core_full_text" and doc.source in {"biorxiv", "medrxiv"}:
        return "preprint_jats"
    if doc.doc_type == "core_full_text":
        return "open_pdf"
    return "abstract_only"


def _source_ids(doc: RAGDocument) -> dict[str, str]:
    metadata = dict(doc.metadata or {})
    return {
        "doc_id": doc.doc_id,
        "source_id": doc.source_id,
        "doi": doc.doi,
        "pmid": str(metadata.get("pmid") or ""),
        "pmcid": str(metadata.get("pmcid") or ""),
        "semantic_scholar_id": str(metadata.get("s2_paper_id") or ""),
        "openalex_id": str(metadata.get("openalex_id") or ""),
    }


def _deduplicate_documents(documents: list[RAGDocument]) -> list[RAGDocument]:
    """Deduplicate by DOI/PMID/PMCID/S2/OpenAlex/normalized title with full-text preference."""
    by_key: dict[str, RAGDocument] = {}
    order: list[str] = []
    for doc in documents:
        key = _document_dedupe_key(doc)
        if not key:
            key = f"doc:{doc.doc_id}"
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = doc
            order.append(key)
            continue
        by_key[key] = _prefer_document(existing, doc)
    return [by_key[key] for key in order]


def _document_dedupe_key(doc: RAGDocument) -> str:
    metadata = dict(doc.metadata or {})
    candidates = [
        doc.doi,
        metadata.get("pmid"),
        metadata.get("pmcid"),
        metadata.get("s2_paper_id"),
        metadata.get("openalex_id"),
    ]
    for item in candidates:
        value = str(item or "").strip().lower()
        if value:
            return value
    title = re.sub(r"\W+", " ", str(doc.title or "").lower()).strip()
    return f"title:{title}" if title else ""


def _prefer_document(left: RAGDocument, right: RAGDocument) -> RAGDocument:
    rank = {"pmc_xml": 4, "preprint_jats": 3, "open_pdf": 2, "abstract_only": 1, "": 0}
    if rank.get(_full_text_status(right), 0) > rank.get(_full_text_status(left), 0):
        primary, secondary = right, left
    else:
        primary, secondary = left, right
    merged_metadata = {**dict(secondary.metadata or {}), **dict(primary.metadata or {})}
    primary.metadata = merged_metadata
    if not primary.doi and secondary.doi:
        primary.doi = secondary.doi
    return primary


def _important_tokens(text: str) -> set[str]:
    stop = {
        "the", "and", "for", "with", "from", "that", "this", "into", "using",
        "single", "cell", "cells", "paper", "study", "analysis", "dataset",
    }
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9]+", str(text or "").lower())
        if len(token) >= 4 and token not in stop
    }
