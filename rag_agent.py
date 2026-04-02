from __future__ import annotations

import hashlib
import json
import re
from typing import Dict, Iterable, List

import textgrad as tg

from config import Config
from rag_sources import fetch_core_document
from rag_store import RAGStore
from rag_types import ConsultantRAGContext, PromotedPaper, RAGDocument, RAGHit


def _dedupe_hits(hits: Iterable[RAGHit]) -> List[RAGHit]:
    ordered: List[RAGHit] = []
    seen = set()
    for hit in hits:
        if hit.doc_id in seen:
            continue
        seen.add(hit.doc_id)
        ordered.append(hit)
    return ordered


def _extract_json(text: str) -> object:
    cleaned = str(text or "").strip()
    match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group(1).strip()
    return json.loads(cleaned)


class ConsultantRAGAgent:
    def __init__(self, *, root_dir: str, engine_name: str, embedding_backend: str = "local", embedding_model: str | None = None):
        self.store = RAGStore(root_dir=root_dir, embedding_backend=embedding_backend, embedding_model=embedding_model)
        self.store.require_general_index()
        self.general_documents = self.store.load_general_documents()
        self.engine = tg.get_engine(engine_name, max_tokens=3000)

    def _query_hash(self, consultant_type: str, query_text: str) -> str:
        payload = f"{consultant_type}\n{query_text}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def _balanced_hits(self, hits: List[RAGHit], per_source_cap: Dict[str, int], keep: int) -> List[RAGHit]:
        counts: Dict[str, int] = {}
        selected: List[RAGHit] = []
        for hit in _dedupe_hits(hits):
            limit = per_source_cap.get(hit.source, keep)
            if counts.get(hit.source, 0) >= limit:
                continue
            counts[hit.source] = counts.get(hit.source, 0) + 1
            selected.append(hit)
            if len(selected) >= keep:
                break
        return selected

    def _build_prior_query(self, config: Config, background: str) -> str:
        return (
            "single-cell prior-guided unsupervised learning biological prior gene set pathway "
            "gene regulatory network regulon knowledge graph interpretable deep learning "
            f"task={config.task_type} metrics={config.metrics}\n"
            f"dataset_summary={config.feat_stats}\n"
            f"prior_resources={config.prior_resource_summary}\n"
            f"background={background}"
        )

    def _build_main_query(self, config: Config, background: str, prior_plan: str, prior_schema_json: str) -> str:
        return (
            "single-cell unsupervised representation learning clustering ARI NMI benchmarking "
            "prior-guided VAE GNN transformer contrastive preprocessing prior alignment\n"
            f"dataset_summary={config.feat_stats}\n"
            f"prior_plan={prior_plan}\n"
            f"prior_schema={prior_schema_json}\n"
            f"background={background}"
        )

    def _promote_papers(self, consultant_type: str, query_text: str, hits: List[RAGHit]) -> List[PromotedPaper]:
        paper_hits = [hit for hit in hits if hit.source in {"pubmed", "biorxiv"}][:10]
        if not paper_hits:
            return []
        candidate_lines = []
        for idx, hit in enumerate(paper_hits, start=1):
            candidate_lines.append(
                "\n".join(
                    [
                        f"[{idx}] doc_id={hit.doc_id}",
                        f"title={hit.title}",
                        f"source={hit.source}",
                        f"published={hit.published or 'unknown'}",
                        f"snippet={hit.snippet}",
                        f"url={hit.url}",
                    ]
                )
            )
        prompt = (
            "You are selecting core papers for a consultant RAG workflow.\n"
            f"Consultant type: {consultant_type}\n"
            f"Query: {query_text}\n\n"
            "Choose the 3-5 best paper candidates for deeper full-text enrichment.\n"
            "Prioritize methodological relevance, implementation detail, and diversity.\n"
            "Return ONLY a JSON array of objects with keys: doc_id, priority, reason.\n\n"
            "Candidates:\n"
            + "\n\n".join(candidate_lines)
        )
        try:
            response = self.engine.generate(
                content=prompt,
                system_prompt="Return only valid JSON. Prefer 3 papers unless 4-5 are clearly justified.",
                temperature=0.0,
            )
            payload = _extract_json(response)
            promoted: List[PromotedPaper] = []
            if isinstance(payload, list):
                for item in payload:
                    if not isinstance(item, dict):
                        continue
                    doc_id = str(item.get("doc_id", "")).strip()
                    if not doc_id:
                        continue
                    matching = next((hit for hit in paper_hits if hit.doc_id == doc_id), None)
                    if not matching:
                        continue
                    promoted.append(
                        PromotedPaper(
                            doc_id=doc_id,
                            title=matching.title,
                            source=matching.source,
                            reason=str(item.get("reason", "")).strip() or "Selected for methodological relevance.",
                            priority=int(item.get("priority", len(promoted) + 1) or len(promoted) + 1),
                        )
                    )
            if promoted:
                return sorted(promoted, key=lambda item: item.priority)[:5]
        except Exception:
            pass
        return [
            PromotedPaper(
                doc_id=hit.doc_id,
                title=hit.title,
                source=hit.source,
                reason="Fallback promotion based on general retrieval rank.",
                priority=idx + 1,
            )
            for idx, hit in enumerate(paper_hits[:3])
        ]

    def _ensure_core_documents(self, promoted: List[PromotedPaper]) -> List[RAGDocument]:
        core_documents: List[RAGDocument] = []
        for promoted_paper in promoted:
            base_document = self.general_documents.get(promoted_paper.doc_id)
            if base_document is None:
                continue
            cached = self.store.load_cached_core_document(base_document.doc_id)
            if cached is not None:
                core_documents.append(cached)
                continue
            enriched = fetch_core_document(base_document)
            if enriched is not None:
                core_doc = enriched.document
                core_doc.metadata = {
                    **core_doc.metadata,
                    "promotion_reason": promoted_paper.reason,
                    "has_full_text": enriched.has_full_text,
                    "extracted_methods": enriched.extracted_methods,
                    "enrichment_source": enriched.enrichment_source,
                }
            else:
                # Keep the promoted paper in the core path even when full text is unavailable.
                core_doc = RAGDocument(
                    doc_id=f"{base_document.doc_id}::core",
                    source=base_document.source,
                    source_id=base_document.source_id,
                    title=base_document.title,
                    text=base_document.abstract or base_document.text,
                    abstract=base_document.abstract,
                    url=base_document.url,
                    authors=base_document.authors,
                    published=base_document.published,
                    doi=base_document.doi,
                    doc_type="core_abstract",
                    categories=list(base_document.categories),
                    metadata={
                        **base_document.metadata,
                        "promotion_reason": promoted_paper.reason,
                        "has_full_text": False,
                        "extracted_methods": False,
                        "enrichment_source": "abstract_only",
                    },
                )
            self.store.save_cached_core_document(base_document.doc_id, core_doc)
            core_documents.append(core_doc)
        return core_documents

    def _format_hits(self, title: str, hits: List[RAGHit]) -> str:
        if not hits:
            return f"{title}\n<none>"
        lines = [title]
        for idx, hit in enumerate(hits, start=1):
            published = hit.published or "unknown date"
            lines.extend(
                [
                    f"{idx}. [{hit.source.upper()}] {hit.title} ({published})",
                    f"   score={hit.score:.3f} | type={hit.doc_type}",
                    f"   snippet={hit.snippet}",
                    f"   url={hit.url or '<none>'}",
                ]
            )
        return "\n".join(lines)

    def _build_context(self, consultant_type: str, query_text: str) -> ConsultantRAGContext:
        query_hash = self._query_hash(consultant_type, query_text)
        raw_hits = self.store.search_general(query_text, n_results=18)
        general_hits = self._balanced_hits(raw_hits, {"pubmed": 6, "biorxiv": 6, "github": 4}, keep=10)
        promoted = self._promote_papers(consultant_type, query_text, general_hits)
        core_documents = self._ensure_core_documents(promoted)
        if core_documents:
            # Query-specific metadata keeps the core index reusable without rebuilding it globally.
            query_specific_documents = []
            for document in core_documents:
                clone = RAGDocument.from_dict(document.to_dict())
                clone.metadata = {
                    **clone.metadata,
                    "consultant_type": consultant_type,
                    "query_hash": query_hash,
                }
                query_specific_documents.append(clone)
            self.store.upsert_core_documents(query_specific_documents, consultant_type=consultant_type, query_hash=query_hash)
        core_hits = self.store.search_core(query_text, consultant_type=consultant_type, query_hash=query_hash, n_results=6)
        return ConsultantRAGContext(
            query_text=query_text,
            general_context=self._format_hits("RAG_GENERAL_CONTEXT", general_hits[:8]),
            core_context=self._format_hits("RAG_CORE_CONTEXT", core_hits[:5]),
            general_hits=general_hits,
            core_hits=core_hits,
            promoted_papers=promoted,
        )

    def build_prior_context(self, config: Config, background: str) -> ConsultantRAGContext:
        return self._build_context("prior", self._build_prior_query(config, background))

    def build_main_context(self, config: Config, background: str, prior_plan: str, prior_schema_json: str) -> ConsultantRAGContext:
        return self._build_context("main", self._build_main_query(config, background, prior_plan, prior_schema_json))
