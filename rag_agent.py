from __future__ import annotations

import hashlib
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable, List

import textgrad as tg

from config import Config
from rag_sources import fetch_core_document, fetch_github_documents, fetch_pubmed_documents
from rag_store import RAGStore
from rag_types import ConsultantRAGContext, PromotedPaper, RAGDocument, RAGHit, dedup_key


logger = logging.getLogger(__name__)

_DATASET_KEYWORD_PROMPT = """You are a scientific literature search expert for single-cell genomics.

Generate search queries to find papers and tools about this biological system and how to preprocess this type of data.

DATASET DESCRIPTION:
{dataset_description}

RESEARCH BACKGROUND:
{background}

Return ONLY a JSON object:
{{
  "pubmed_queries": ["boolean AND queries"],
  "github_queries": [
    {{"query": "search tokens", "language": "python", "min_stars": 10}}
  ]
}}

Rules:
- Produce specific tissue, organism, assay, and preprocessing queries.
- Cover both biology and preprocessing.
- Every PubMed query must include at least one dataset-specific biological token.
- Avoid generic searches like "single-cell preprocessing".
"""

_PRIOR_RESOURCE_KEYWORD_PROMPT = """You are a scientific literature search expert for biological knowledge resources.

Generate search queries to find papers and tools describing these specific prior knowledge resources, their coverage, structure, relevance, and limitations for this biological system.

AVAILABLE PRIOR RESOURCES:
{prior_resource_files}

DATASET CONTEXT:
{dataset_description}

Return ONLY a JSON object:
{{
  "pubmed_queries": ["boolean AND queries"],
  "github_queries": [
    {{"query": "search tokens", "language": "python", "min_stars": 10}}
  ]
}}

Rules:
- Name specific resources in every PubMed query.
- Cover coverage, limitations, tissue relevance, and known biases.
- Do not search for general prior learning methods here.
"""

_PRIOR_METHOD_KEYWORD_PROMPT = """You are a scientific literature search expert for prior-guided single-cell analysis.

Generate search queries to find papers and tools about methods for integrating biological priors into deep learning pipelines, and papers about prior-free alternatives for the same type of task.

AVAILABLE PRIOR RESOURCE TYPES:
{prior_resource_types}

DATASET CONTEXT:
{dataset_description}

TASK:
{task_description}

RESEARCH BACKGROUND:
{background}

Return ONLY a JSON object:
{{
  "pubmed_queries": ["boolean AND queries"],
  "github_queries": [
    {{"query": "search tokens", "language": "python", "min_stars": 10}}
  ]
}}

Rules:
- Cover both prior-guided and prior-free methods.
- Include comparative, ablation, benchmark, and "when priors help vs hurt" angles.
- Reference specific prior types from the available list when possible.
"""

_MODEL_KEYWORD_PROMPT = """You are a scientific literature search expert for single-cell deep learning.

The prior consultant has decided on an approach. Generate search queries to find papers and tools about the specific architectures and training strategies that match this plan.

PRIOR DECISION:
{prior_decision}

CHOSEN APPROACH:
{prior_plan}

PRIOR SCHEMA:
{prior_schema}

RESEARCH BACKGROUND:
{background}

Return ONLY a JSON object:
{{
  "pubmed_queries": ["boolean AND queries"],
  "github_queries": [
    {{"query": "search tokens", "language": "python", "min_stars": 10}}
  ]
}}

Rules:
- Be specific to the chosen approach.
- If priors are disabled, focus on prior-free architectures and training strategies for this task.
- Do not retrieve alternative design families unless they are direct comparators useful for the chosen approach.
"""


def _extract_json(text: str) -> object:
    cleaned = str(text or "").strip()
    match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group(1).strip()
    return json.loads(cleaned)


class ConsultantRAGAgent:
    def __init__(self, *, root_dir: str, engine_name: str, embedding_backend: str = "local", embedding_model: str | None = None):
        self.store = RAGStore(root_dir=root_dir, embedding_backend=embedding_backend, embedding_model=embedding_model)
        try:
            self.engine = tg.get_engine(engine_name, max_tokens=3000)
        except TypeError:
            self.engine = tg.get_engine(engine_name)
        self._channel_documents_by_collection: Dict[str, Dict[str, RAGDocument]] = {}
        self._dataset_docs_cache: Dict[str, List[RAGDocument]] = {}

    def ensure_index(self, config: Config, background: str) -> None:
        # Channel-specific indexes are built lazily on demand.
        _ = (config, background)

    def _dataset_summary_json(self, config: Config) -> Dict[str, object]:
        text = str(config.feat_stats or "")
        if "LLM SUMMARY (JSON):" not in text:
            return {}
        try:
            return json.loads(text.split("LLM SUMMARY (JSON):", 1)[-1].strip())
        except Exception:
            return {}

    def _prior_resources_payload(self, config: Config) -> List[Dict[str, Any]]:
        try:
            payload = json.loads(str(config.prior_resource_summary or ""))
        except Exception:
            return []
        resources = payload.get("prior_resources", [])
        return resources if isinstance(resources, list) else []

    def _prior_resource_names(self, config: Config) -> List[str]:
        names: List[str] = []
        for item in self._prior_resources_payload(config):
            file_path = str(item.get("file_path", "")).strip()
            if file_path:
                names.append(Path(file_path).name)
        return names

    def _prior_resource_types(self, config: Config) -> List[str]:
        resource_types: List[str] = []
        for item in self._prior_resources_payload(config):
            file_path = str(item.get("file_path", "")).strip().lower()
            resource_type = str(item.get("resource_type", "")).strip().lower()
            if resource_type:
                resource_types.append(resource_type)
            if "msigdb" in file_path:
                resource_types.append("pathway_gene_sets")
            if "go_terms" in file_path:
                resource_types.append("gene_ontology")
            if "nest" in file_path:
                resource_types.append("gene_regulatory_network")
            if "cell_marker" in file_path:
                resource_types.append("marker_genes")
            if "gene_embedding" in file_path:
                resource_types.append("gene_text_embeddings")
        deduped: List[str] = []
        seen = set()
        for item in resource_types:
            if item and item not in seen:
                seen.add(item)
                deduped.append(item)
        return deduped

    def _channel_hash(self, channel_name: str, payload: Dict[str, Any], keyword_prompt: str) -> str:
        serialized = json.dumps(
            {"channel": channel_name, "payload": payload, "keyword_prompt": keyword_prompt},
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]

    def _validate_keyword_payload(self, payload: object) -> Dict[str, List[object]]:
        if not isinstance(payload, dict):
            raise ValueError(f"Expected keyword payload dict, got {type(payload)}")

        pubmed_queries = [str(item).strip() for item in payload.get("pubmed_queries", []) if str(item).strip()]
        if not pubmed_queries:
            raise ValueError("Keyword payload must include a non-empty pubmed_queries list")

        github_queries: List[Dict[str, object]] = []
        raw_github = payload.get("github_queries", [])
        if not isinstance(raw_github, list):
            raise ValueError("Keyword payload must include github_queries as a list")
        for item in raw_github:
            if not isinstance(item, dict):
                continue
            query = str(item.get("query", "")).strip()
            if not query:
                continue
            language = str(item.get("language", "python")).strip() or "python"
            try:
                min_stars = int(item.get("min_stars", 10) or 10)
            except (TypeError, ValueError):
                min_stars = 10
            github_queries.append(
                {
                    "query": query,
                    "language": language,
                    "min_stars": max(0, min_stars),
                }
            )
        if not github_queries:
            raise ValueError("Keyword payload must include at least one valid github_queries entry")
        return {"pubmed_queries": pubmed_queries, "github_queries": github_queries}

    def _persist_json(self, path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def _generate_search_keywords(self, *, channel_name: str, prompt: str, max_attempts: int = 3) -> Dict[str, List[object]]:
        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                response = self.engine.generate(
                    content=prompt,
                    system_prompt="Return only valid JSON. Be specific to the dataset and task.",
                    temperature=0.0,
                )
                validated = self._validate_keyword_payload(_extract_json(response))
                logger.info(
                    "Generated runtime RAG queries for %s on attempt %d: %d PubMed, %d GitHub",
                    channel_name,
                    attempt,
                    len(validated["pubmed_queries"]),
                    len(validated["github_queries"]),
                )
                return validated
            except Exception as exc:
                last_error = exc
                logger.warning("Runtime RAG keyword generation failed for %s on attempt %d/%d: %s", channel_name, attempt, max_attempts, exc)
        raise RuntimeError(f"Failed to generate runtime RAG keywords for {channel_name}") from last_error

    def _load_or_fetch_channel_documents(self, *, session_key: str, channel_name: str, keyword_prompt: str) -> List[RAGDocument]:
        documents_path = self.store.channel_documents_path(session_key, channel_name)
        keywords_path = self.store.channel_keywords_path(session_key, channel_name)
        if documents_path.exists():
            cached_documents = self.store.deduplicate_documents(self.store.load_documents(documents_path))
            if cached_documents:
                logger.info("Loaded runtime RAG cache for %s/%s with %d documents", session_key, channel_name, len(cached_documents))
                return cached_documents
            logger.warning("Runtime RAG cache for %s/%s was empty; rebuilding", session_key, channel_name)

        keywords = self._generate_search_keywords(channel_name=channel_name, prompt=keyword_prompt)
        self._persist_json(keywords_path, keywords)

        all_documents: List[RAGDocument] = []
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {
                pool.submit(fetch_pubmed_documents, keywords["pubmed_queries"], 15): "pubmed",
                pool.submit(fetch_github_documents, keywords["github_queries"], 5): "github",
            }
            for future in as_completed(futures):
                source_name = futures[future]
                try:
                    fetched = future.result()
                    logger.info("Fetched %d runtime RAG documents from %s for %s", len(fetched), source_name, channel_name)
                    all_documents.extend(fetched)
                except Exception as exc:
                    logger.warning("Runtime RAG fetch failed for %s (%s): %s", channel_name, source_name, exc)

        deduped_documents = self.store.deduplicate_documents(all_documents)
        if not deduped_documents:
            raise RuntimeError(f"Runtime RAG produced no documents for {channel_name}")
        self.store.save_documents(documents_path, deduped_documents)
        logger.info("Persisted runtime RAG cache for %s/%s with %d documents", session_key, channel_name, len(deduped_documents))
        return deduped_documents

    def _ensure_channel_index(self, *, channel_name: str, payload: Dict[str, Any], keyword_prompt: str) -> str:
        session_key = self._channel_hash(channel_name, payload, keyword_prompt)
        collection_name = self.store.runtime_collection_name(session_key, channel_name)
        documents = self._load_or_fetch_channel_documents(session_key=session_key, channel_name=channel_name, keyword_prompt=keyword_prompt)
        self.store.build_runtime_index(collection_name, documents, rebuild=True)
        self._channel_documents_by_collection[collection_name] = {document.doc_id: document for document in documents}
        return collection_name

    def _search_channel_hits(self, *, collection_name: str, query_text: str, n_results: int = 24) -> List[RAGHit]:
        seen_keys = set()
        hits: List[RAGHit] = []
        for hit in self.store.search_runtime(collection_name, query_text, n_results=n_results):
            if hit.source not in {"pubmed", "github"}:
                continue
            key = dedup_key(hit.doc_id, hit.doi, hit.title)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            hits.append(hit)
        return hits

    def _document_hits(self, documents: Iterable[RAGDocument]) -> List[RAGHit]:
        hits: List[RAGHit] = []
        for document in documents:
            snippet = re.sub(r"\s+", " ", str(document.abstract or document.text or "")).strip()[:320]
            hits.append(
                RAGHit(
                    doc_id=document.doc_id,
                    title=document.title,
                    source=document.source,
                    score=-1.0,
                    snippet=snippet,
                    url=document.url,
                    doc_type=document.doc_type,
                    source_id=document.source_id,
                    published=document.published,
                    doi=document.doi,
                    is_runtime_fallback=False,
                    metadata=dict(document.metadata),
                )
            )
        return hits

    def _select_papers(self, channel_name: str, query_text: str, hits: List[RAGHit], keep: int = 5) -> List[PromotedPaper]:
        candidates = hits[:12]
        if not candidates:
            return []
        candidate_lines = []
        for idx, hit in enumerate(candidates, start=1):
            candidate_lines.append(
                "\n".join(
                    [
                        f"[{idx}] doc_id={hit.doc_id}",
                        f"title={hit.title}",
                        f"source={hit.source}",
                        f"published={hit.published or 'unknown'}",
                        f"snippet={hit.snippet}",
                        f"url={hit.url or '<none>'}",
                    ]
                )
            )
        prompt = (
            f"You are selecting literature and tools for {channel_name}.\n"
            f"Query: {query_text}\n\n"
            f"Choose exactly the best {min(keep, len(candidates))} candidates.\n"
            "Return ONLY a JSON array of objects with keys: doc_id, priority, reason.\n\n"
            "Candidates:\n"
            + "\n\n".join(candidate_lines)
        )
        try:
            response = self.engine.generate(
                content=prompt,
                system_prompt="Return only valid JSON. Prefer diverse, high-signal papers and tools.",
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
                    match = next((hit for hit in candidates if hit.doc_id == doc_id), None)
                    if match is None:
                        continue
                    raw_priority = item.get("priority", len(promoted) + 1)
                    try:
                        priority = int(raw_priority)
                    except (TypeError, ValueError):
                        priority = len(promoted) + 1
                    promoted.append(
                        PromotedPaper(
                            doc_id=doc_id,
                            title=match.title,
                            source=match.source,
                            reason=str(item.get("reason", "")).strip() or "Selected for relevance.",
                            priority=priority,
                        )
                    )
            if promoted:
                promoted = sorted(promoted, key=lambda item: item.priority)
                seen_ids = set()
                ordered: List[PromotedPaper] = []
                for item in promoted:
                    if item.doc_id in seen_ids:
                        continue
                    seen_ids.add(item.doc_id)
                    ordered.append(item)
                    if len(ordered) >= keep:
                        break
                if ordered:
                    return ordered
        except Exception as exc:
            logger.warning("LLM paper selection failed for %s: %s", channel_name, exc)
        return [
            PromotedPaper(
                doc_id=hit.doc_id,
                title=hit.title,
                source=hit.source,
                reason=f"Fallback selection for {channel_name}.",
                priority=idx + 1,
            )
            for idx, hit in enumerate(candidates[:keep])
        ]

    def _ensure_full_text_documents(self, selected: List[PromotedPaper], documents_by_id: Dict[str, RAGDocument]) -> List[RAGDocument]:
        enriched_docs: List[RAGDocument] = []
        for paper in selected:
            base_document = documents_by_id.get(paper.doc_id)
            if base_document is None:
                continue
            if base_document.source not in {"pubmed", "biorxiv"}:
                enriched_docs.append(
                    RAGDocument(
                        doc_id=base_document.doc_id,
                        source=base_document.source,
                        source_id=base_document.source_id,
                        title=base_document.title,
                        text=base_document.text,
                        abstract=base_document.abstract,
                        url=base_document.url,
                        authors=base_document.authors,
                        published=base_document.published,
                        doi=base_document.doi,
                        doc_type=base_document.doc_type,
                        categories=list(base_document.categories),
                        metadata={**base_document.metadata, "selection_reason": paper.reason, "has_full_text": False},
                    )
                )
                continue
            cached = self.store.load_cached_core_document(base_document.doc_id)
            if cached is not None:
                cached.metadata = {**cached.metadata, "selection_reason": paper.reason}
                enriched_docs.append(cached)
                continue
            enriched = fetch_core_document(base_document)
            if enriched is not None:
                core_doc = enriched.document
                core_doc.metadata = {
                    **core_doc.metadata,
                    "selection_reason": paper.reason,
                    "has_full_text": enriched.has_full_text,
                    "extracted_methods": enriched.extracted_methods,
                    "enrichment_source": enriched.enrichment_source,
                }
            else:
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
                    metadata={**base_document.metadata, "selection_reason": paper.reason, "has_full_text": False},
                )
            self.store.save_cached_core_document(base_document.doc_id, core_doc)
            enriched_docs.append(core_doc)
        return enriched_docs

    def _format_documents(self, label: str, documents: List[RAGDocument]) -> str:
        if not documents:
            return f"{label}\n<none>"
        lines = [label]
        for idx, document in enumerate(documents[:5], start=1):
            excerpt = re.sub(r"\s+", " ", str(document.text or document.abstract or "")).strip()
            excerpt = excerpt[:900].rsplit(" ", 1)[0].strip() if len(excerpt) > 900 else excerpt
            reason = str(document.metadata.get("selection_reason", "")).strip()
            lines.extend(
                [
                    f"{idx}. [{document.source.upper()}] {document.title} ({document.published or 'unknown date'})",
                    f"   type={document.doc_type}",
                    f"   reason={reason or 'Selected for relevance.'}",
                    f"   excerpt={excerpt or '<none>'}",
                    f"   url={document.url or '<none>'}",
                ]
            )
        return "\n".join(lines)

    def _channel_documents(self, *, channel_name: str, payload: Dict[str, Any], keyword_prompt: str, query_text: str, keep: int = 5) -> List[RAGDocument]:
        collection_name = self._ensure_channel_index(channel_name=channel_name, payload=payload, keyword_prompt=keyword_prompt)
        paper_hits = self._search_channel_hits(collection_name=collection_name, query_text=query_text, n_results=20)
        documents_by_id = self._channel_documents_by_collection.get(collection_name, {})
        selected = self._select_papers(channel_name, query_text, paper_hits, keep=keep)
        selected_ids = [paper.doc_id for paper in selected]
        if len(selected_ids) < keep:
            for hit in paper_hits:
                if hit.doc_id not in selected_ids:
                    selected_ids.append(hit.doc_id)
                if len(selected_ids) >= keep:
                    break
            selected = [
                PromotedPaper(
                    doc_id=doc_id,
                    title=documents_by_id[doc_id].title,
                    source=documents_by_id[doc_id].source,
                    reason="Filled from retrieval rank.",
                    priority=idx + 1,
                )
                for idx, doc_id in enumerate(selected_ids[:keep])
                if doc_id in documents_by_id
            ]
        return self._ensure_full_text_documents(selected[:keep], documents_by_id)

    def _dataset_channel(self, config: Config, background: str) -> List[RAGDocument]:
        summary_json = self._dataset_summary_json(config)
        dataset_summary = " ".join(
            part
            for part in [
                str(summary_json.get("modality_1_summary", "")).strip(),
                str(summary_json.get("modality_2_summary", "")).strip(),
                str(summary_json.get("notes", "")).strip(),
                str(background or "").strip(),
            ]
            if part
        )
        dataset_summary = dataset_summary or str(config.feat_stats or "")
        payload = {
            "feat_stats": str(config.feat_stats or ""),
            "background": str(background or ""),
        }
        cache_key = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        cached = self._dataset_docs_cache.get(cache_key)
        if cached is not None:
            return cached
        keyword_prompt = _DATASET_KEYWORD_PROMPT.format(
            dataset_description=str(config.feat_stats or "")[:2200],
            background=str(background or "")[:1200],
        )
        query_text = f"single-cell dataset tissue assay biology context {dataset_summary}"
        documents = self._channel_documents(channel_name="dataset", payload=payload, keyword_prompt=keyword_prompt, query_text=query_text)
        self._dataset_docs_cache[cache_key] = documents
        return documents

    def _prior_resource_channel(self, config: Config, background: str) -> List[RAGDocument]:
        resource_names = self._prior_resource_names(config)
        payload = {
            "prior_resource_summary": str(config.prior_resource_summary or ""),
            "feat_stats": str(config.feat_stats or ""),
            "resource_names": resource_names,
        }
        keyword_prompt = _PRIOR_RESOURCE_KEYWORD_PROMPT.format(
            prior_resource_files="\n".join(resource_names) or "<none>",
            dataset_description=str(config.feat_stats or "")[:1600],
        )
        query_text = (
            "single-cell prior resource coverage limitations tissue specificity database relevance\n"
            f"resources={', '.join(resource_names)}\nbackground={background}"
        )
        return self._channel_documents(channel_name="prior_resources", payload=payload, keyword_prompt=keyword_prompt, query_text=query_text)

    def _prior_method_channel(self, config: Config, background: str) -> List[RAGDocument]:
        prior_resource_types = self._prior_resource_types(config)
        payload = {
            "prior_resource_types": prior_resource_types,
            "feat_stats": str(config.feat_stats or ""),
            "background": str(background or ""),
            "task_type": str(config.task_type or ""),
            "learning_type": str(config.learning_type or ""),
            "metrics": config.metrics,
        }
        task_description = f"{config.task_type} / {config.learning_type} optimized for metrics {config.metrics}"
        keyword_prompt = _PRIOR_METHOD_KEYWORD_PROMPT.format(
            prior_resource_types=", ".join(prior_resource_types) or "unknown",
            dataset_description=str(config.feat_stats or "")[:1600],
            task_description=task_description,
            background=str(background or "")[:1200],
        )
        query_text = (
            "single-cell prior-guided versus prior-free benchmark ablation comparison\n"
            f"prior_resource_types={prior_resource_types}\n"
            f"task={task_description}\nbackground={background}"
        )
        return self._channel_documents(channel_name="prior_methods", payload=payload, keyword_prompt=keyword_prompt, query_text=query_text)

    def _model_design_channel(
        self,
        config: Config,
        background: str,
        dataset_context: str,
        prior_plan: str,
        prior_schema_json: str,
        prior_decision_json: str,
    ) -> List[RAGDocument]:
        if config.use_priors():
            logger.info("Reusing prior_methods runtime RAG documents for model_design because priors are enabled")
            return self._prior_method_channel(config, background)

        dataset_context_text = str(dataset_context or "").strip()
        payload = {
            "feat_stats": str(config.feat_stats or ""),
            "background": str(background or ""),
            "dataset_context": dataset_context_text,
            "task_type": str(config.task_type or ""),
            "learning_type": str(config.learning_type or ""),
            "metrics": config.metrics,
        }
        keyword_prompt = _MODEL_KEYWORD_PROMPT.format(
            prior_decision="use_priors=false",
            prior_plan=(
                f"Design a prior-free single-cell model for task={config.task_type}, "
                f"learning_type={config.learning_type}, metrics={config.metrics}"
            )[:1600],
            prior_schema="<none>",
            background=(f"{str(background or '')[:800]}\n\nDATASET RAG CONTEXT:\n{dataset_context_text[:2000]}")[:2800],
        )
        query_text = (
            "single-cell prior-free model design architecture training losses optimization\n"
            f"task={config.task_type}\nlearning_type={config.learning_type}\nmetrics={config.metrics}\n"
            f"dataset={config.feat_stats}\n"
            f"dataset_context={dataset_context_text}\nbackground={background}"
        )
        return self._channel_documents(channel_name="model_design", payload=payload, keyword_prompt=keyword_prompt, query_text=query_text)

    def build_prior_context(self, config: Config, background: str) -> ConsultantRAGContext:
        self.ensure_index(config, background)
        query_text = f"prior_consultant\n{config.feat_stats}\n{config.prior_resource_summary}\n{background}"
        dataset_documents = self._dataset_channel(config, background)
        prior_resource_documents = self._prior_resource_channel(config, background)
        prior_method_documents = self._prior_method_channel(config, background)
        return ConsultantRAGContext(
            query_text=query_text,
            dataset_context=self._format_documents("RAG_DATASET_CONTEXT", dataset_documents),
            prior_resource_context=self._format_documents("RAG_PRIOR_RESOURCE_CONTEXT", prior_resource_documents),
            prior_method_context=self._format_documents("RAG_PRIOR_METHOD_CONTEXT", prior_method_documents),
            model_design_context="RAG_MODEL_DESIGN_CONTEXT\n<none>",
            dataset_hits=self._document_hits(dataset_documents),
            prior_resource_hits=self._document_hits(prior_resource_documents),
            prior_method_hits=self._document_hits(prior_method_documents),
            model_design_hits=[],
        )

    def build_main_context(
        self,
        config: Config,
        background: str,
        prior_plan: str,
        prior_schema_json: str,
        prior_decision_json: str,
    ) -> ConsultantRAGContext:
        self.ensure_index(config, background)
        query_text = f"main_consultant\n{config.feat_stats}\n{prior_plan}\n{prior_schema_json}\n{prior_decision_json}\n{background}"
        dataset_documents = self._dataset_channel(config, background)
        dataset_context_text = self._format_documents("RAG_DATASET_CONTEXT", dataset_documents)
        model_design_documents = self._model_design_channel(
            config,
            background,
            dataset_context_text,
            prior_plan,
            prior_schema_json,
            prior_decision_json,
        )
        return ConsultantRAGContext(
            query_text=query_text,
            dataset_context=dataset_context_text,
            prior_resource_context="RAG_PRIOR_RESOURCE_CONTEXT\n<none>",
            prior_method_context="RAG_PRIOR_METHOD_CONTEXT\n<none>",
            model_design_context=self._format_documents("RAG_MODEL_DESIGN_CONTEXT", model_design_documents),
            dataset_hits=self._document_hits(dataset_documents),
            prior_resource_hits=[],
            prior_method_hits=[],
            model_design_hits=self._document_hits(model_design_documents),
        )
