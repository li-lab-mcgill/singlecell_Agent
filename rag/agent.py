from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import textgrad as tg

from pipelines.config import Config
from rag.sources import fetch_core_document, normalize_section_type, fetch_pubmed_documents
from rag.store_backend import RAGStore
from rag.types import PromotedPaper, RAGDocument, RAGHit, dedup_key


logger = logging.getLogger(__name__)

MAX_PUBMED_RESULTS_PER_QUERY = 50
MAX_PMC_CANDIDATES_PER_CHANNEL = 50
DEFAULT_PUBMED_QUERY_COUNT = 10
PRIOR_METHOD_PUBMED_QUERY_COUNT = 20
DEFAULT_SUBQUERY_COUNT = 4
DEFAULT_CHANNEL_TOP_K = 5
DEFAULT_CHANNEL_SEARCH_HITS = 24
DEFAULT_RRF_K = 60

BASE_QUERIES = {
    "dataset": "Need papers describing expected characteristics and challenges of the dataset such as cell populations, marker genes, heterogeneity, and preprocessing/QC issues.",
    "prior_resources": "Need papers describing how the available prior resources are structured, what biological signal they capture, and what their coverage, limitations, and biases are for this dataset context.",
    "prior_methods": "Need papers describing recent prior-guided and prior-free methods for {task} in {dataset}, including how biological priors are incorporated, what baselines are appropriate, and when priors help or hurt.",
    "benchmark": "Need papers describing recent benchmark and evaluation practices for {task} in {dataset}, including what metrics, baselines, ablations, and evidence are used to judge whether a method works well.",
}

CHANNEL_LABELS = {
    "dataset": "RAG_DATASET_CONTEXT",
    "prior_resources": "RAG_PRIOR_RESOURCE_CONTEXT",
    "prior_methods": "RAG_PRIOR_METHOD_CONTEXT",
    "benchmark": "RAG_BENCHMARK_CONTEXT",
    "model_design": "RAG_MODEL_DESIGN_CONTEXT",
}

_CHANNEL_KEYWORD_PROMPT = """You are a scientific literature search expert.

Generate PubMed search queries to retrieve papers specifically related to the background and relevant to or extending the base query. 
The background may include descriptions of the dataset, available prior resources, and the task. 
Use the background to understand the retrieval context and base query as the retrieval intent.

BACKGROUND:
{background}

BASE_QUERY:
{base_query}

Return ONLY a JSON object:
{{
  "pubmed_queries": ["PubMed-style Boolean queries using AND/OR and quotes where useful"]
}}

Rules:
- Generate short, high-recall PubMed queries.
- Use the background and base query as the only source of retrieval intent.
- Prefer one retrieval theme per query.
- Do not use PubMed filters such as pmc[Filter], review[Filter], english[Filter], or date filters.
- Avoid unrelated modalities or tasks not supported by the background.
"""

_CHANNEL_SUBQUERY_PROMPT = """You are generating semantic retrieval subqueries for a biomedical RAG pipeline.

BACKGROUND:
{background}

BASE_QUERY:
{base_query}

Task:
Generate {n_subqueries} independent subqueries that decompose the base query into distinct retrieval needs that are more specific for the provided background.

For each subquery, also generate one hypothetical scientific abstract written in the style of a real paper abstract. The abstract should use terminology and phrasing likely to appear in relevant papers.

Return ONLY a JSON object:
{{
  "items": [
    {{
      "subquery": "<short retrieval-friendly subquery>",
      "hyde_abstract": "<concise scientific abstract>"
    }}
  ]
}}

Requirements:
- Use the base query unchanged as the retrieval intent; do not redesign it.
- Subqueries must be non-overlapping and complementary.
- Use terminology that authors actually use in paper titles and abstracts.
- Do not use planning language such as "need papers about" or "information on".
- Keep subqueries short, concrete, and retrieval-friendly.
- Keep each abstract concise, scientific, and specific to the subquery.
- Do not invent citations, authors, or journal names.
"""

_PAPER_SUMMARY_PROMPT = """You are summarizing a biomedical paper for a consultant agent.

Return ONLY valid JSON:
{{
  "objective": "<string>",
  "key_methods": "<string>",
  "main_findings": "<string>",
  "limitations": "<string>"
}}

Paper title: {title}
Publication date: {published}

Abstract:
{abstract}

Methods:
{methods}

Results:
{results}

Discussion:
{discussion}
"""


def _extract_json(text: str) -> object:
    cleaned = str(text or "").strip()
    match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group(1).strip()
    return json.loads(cleaned)


def _json_dump(payload: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _shorten(text: str, max_chars: int = 600) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 3)].rstrip() + "..."


def _subquery_rank_score(rank: int, score: float) -> float:
    safe_rank = max(1, rank)
    safe_score = max(0.0, float(score or 0.0))
    return safe_score / float(safe_rank)


def _strip_unbalanced_parentheses(text: str) -> str:
    chars: List[str] = []
    depth = 0
    for ch in str(text or ""):
        if ch == "(":
            depth += 1
            chars.append(ch)
        elif ch == ")":
            if depth > 0:
                depth -= 1
                chars.append(ch)
        else:
            chars.append(ch)
    if depth <= 0:
        return "".join(chars)
    result = "".join(chars)
    while depth > 0:
        idx = result.rfind("(")
        if idx < 0:
            break
        result = result[:idx] + result[idx + 1 :]
        depth -= 1
    return result


class ConsultantRAGAgent:
    def __init__(self, *, root_dir: str, engine_name: str, embedding_backend: str = "local", embedding_model: str | None = None):
        self.store = RAGStore(root_dir=root_dir, embedding_backend=embedding_backend, embedding_model=embedding_model)
        try:
            self.engine = tg.get_engine(engine_name, max_tokens=3000)
        except TypeError:
            self.engine = tg.get_engine(engine_name)
        self._channel_documents_by_collection: Dict[str, Dict[str, RAGDocument]] = {}
        self._paper_documents_by_id: Dict[str, RAGDocument] = {}
        self._channel_cache_keys: Dict[Tuple[str, str], str] = {}
        self._prepared_channel_contexts: Dict[str, Dict[str, Any]] = {}

    def ensure_index(self, config: Config, background: str) -> None:
        _ = (config, background)

    def reset_run_state(self) -> None:
        self.store.reset_runtime_artifacts()
        self._channel_documents_by_collection.clear()
        self._paper_documents_by_id.clear()
        self._channel_cache_keys.clear()
        self._prepared_channel_contexts.clear()

    def _dataset_summary_json(self, config: Config) -> Dict[str, object]:
        text = str(config.feat_stats or "")
        if "LLM SUMMARY (JSON):" not in text:
            return {}
        try:
            return json.loads(text.split("LLM SUMMARY (JSON):", 1)[-1].strip())
        except Exception:
            return {}

    def _dataset_descriptor(self, config: Config, background: str = "") -> str:
        summary_json = self._dataset_summary_json(config)
        pieces = [
            str(summary_json.get("modality_1_summary", "")).strip(),
            str(summary_json.get("modality_2_summary", "")).strip(),
            str(summary_json.get("notes", "")).strip(),
        ]
        descriptor = " ".join(part for part in pieces if part)
        if descriptor:
            return descriptor
        fallback = str(config.feat_stats or "").strip()
        if fallback:
            return fallback
        return str(background or "").strip()

    def _task_descriptor(self, config: Config, background: str = "") -> str:
        task_match = re.search(
            r"(?ims)^\s*TASK:\s*(.*?)\s*(?:\n\s*\n|^\s*[A-Z][A-Z _]+:\s*|\Z)",
            str(background or ""),
        )
        if task_match:
            extracted = re.sub(r"\s+", " ", task_match.group(1)).strip()
            if extracted:
                return extracted
        return "representation learning and clustering"

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

    def _resolve_base_query(self, channel_name: str, config: Config, background: str) -> str:
        base_query = BASE_QUERIES[channel_name]
        if "{task}" not in base_query and "{dataset}" not in base_query:
            return base_query
        return base_query.format(
            task=self._task_descriptor(config, background),
            dataset=self._dataset_descriptor(config, background),
        )

    def _build_keyword_background(self, *, channel_name: str, config: Config, background: str) -> str:
        dataset_description = self._dataset_descriptor(config, background)
        resource_names = self._prior_resource_names(config)
        resource_types = self._prior_resource_types(config)
        task_description = self._task_descriptor(config, background)

        if channel_name == "dataset":
            return f"DATASET DESCRIPTION:\n{dataset_description}"
        if channel_name == "prior_resources":
            return (
                f"AVAILABLE PRIOR RESOURCES:\n{', '.join(resource_names) or '<none>'}\n\n"
                f"DATASET CONTEXT:\n{dataset_description}"
            )
        if channel_name == "prior_methods":
            return (
                f"AVAILABLE PRIOR RESOURCE TYPES:\n{', '.join(resource_types) or '<none>'}\n\n"
                f"DATASET CONTEXT:\n{dataset_description}\n\n"
                f"TASK:\n{task_description}"
            )
        if channel_name == "benchmark":
            return (
                f"DATASET CONTEXT:\n{dataset_description}\n\n"
                f"TASK:\n{task_description}"
            )
        raise ValueError(f"Unsupported keyword background channel: {channel_name}")

    def _pubmed_query_count(self, channel_name: str) -> int:
        if channel_name == "prior_methods":
            return PRIOR_METHOD_PUBMED_QUERY_COUNT
        return DEFAULT_PUBMED_QUERY_COUNT

    def _channel_hash(self, channel_name: str, payload: Dict[str, Any], base_query: str, background: str) -> str:
        serialized = json.dumps(
            {
                "channel": channel_name,
                "payload": payload,
                "base_query": base_query,
                "background": background,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]

    def _sanitize_pubmed_query(self, query: str) -> str:
        cleaned = str(query or "").strip()
        if not cleaned:
            return ""
        cleaned = re.sub(r"\bpmc\s*\[\s*Filter\s*\]", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\breview\s*\[\s*Filter\s*\]", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\benglish\s*\[\s*Filter\s*\]", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        cleaned = re.sub(r"\(\s*\(", "(", cleaned)
        cleaned = re.sub(r"\)\s*\)", ")", cleaned)
        cleaned = re.sub(r"\(\s+", "(", cleaned)
        cleaned = re.sub(r"\s+\)", ")", cleaned)
        cleaned = re.sub(r"\s+(AND|OR)\s+\)", ")", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\(\s+(AND|OR)\s+", "(", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,")
        cleaned = re.sub(r"(?:\bAND\b|\bOR\b)\s*$", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = _strip_unbalanced_parentheses(cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,")
        and_count = len(re.findall(r"\bAND\b", cleaned, flags=re.IGNORECASE))
        if and_count > 3:
            parts = re.split(r"\bAND\b", cleaned, flags=re.IGNORECASE)
            cleaned = " AND ".join(part.strip() for part in parts[:3] if part.strip())
        return cleaned.strip()

    def _validate_keyword_payload(self, payload: object) -> List[str]:
        if not isinstance(payload, dict):
            raise ValueError(f"Expected keyword payload dict, got {type(payload)}")
        pubmed_queries = [
            self._sanitize_pubmed_query(item)
            for item in payload.get("pubmed_queries", [])
            if str(item).strip()
        ]
        pubmed_queries = [query for query in pubmed_queries if query]
        if not pubmed_queries:
            raise ValueError("Keyword payload must include a non-empty pubmed_queries list")
        return pubmed_queries

    def _validate_subquery_payload(self, payload: object) -> List[Dict[str, str]]:
        if not isinstance(payload, dict):
            raise ValueError(f"Expected subquery payload dict, got {type(payload)}")
        raw_items = payload.get("items", [])
        if not isinstance(raw_items, list) or not raw_items:
            raise ValueError("Subquery payload must include a non-empty items list")

        items: List[Dict[str, str]] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            subquery = str(item.get("subquery", "")).strip()
            hyde_abstract = str(item.get("hyde_abstract", "")).strip()
            if not subquery or not hyde_abstract:
                continue
            items.append({"subquery": subquery, "hyde_abstract": hyde_abstract})
        if not items:
            raise ValueError("Subquery payload must contain valid items with subquery and hyde_abstract")
        return items

    def _validate_channel_plan(self, payload: object) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError(f"Expected channel plan payload dict, got {type(payload)}")
        return {
            "pubmed_queries": self._validate_keyword_payload(payload),
            "items": self._validate_subquery_payload(payload),
        }

    def _generate_pubmed_queries(self, *, channel_name: str, config: Config, background: str, base_query: str, n_queries: int = DEFAULT_PUBMED_QUERY_COUNT, max_attempts: int = 3) -> List[str]:
        keyword_background = self._build_keyword_background(
            channel_name=channel_name,
            config=config,
            background=str(background or "")[:2200],
        )
        prompt = _CHANNEL_KEYWORD_PROMPT.format(
            background=keyword_background[:3500],
            base_query=base_query,
        )
        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                response = self.engine.generate(
                    content=prompt,
                    system_prompt="Return only valid JSON. Keep PubMed queries short, high-recall, grounded in the background and base query, and filter-free.",
                    temperature=0.0,
                )
                pubmed_queries = self._validate_keyword_payload(_extract_json(response))
                if len(pubmed_queries) > n_queries:
                    pubmed_queries = pubmed_queries[:n_queries]
                logger.info(
                    "Generated keyword queries for %s on attempt %d: %d queries",
                    channel_name,
                    attempt,
                    len(pubmed_queries),
                )
                return pubmed_queries
            except Exception as exc:
                last_error = exc
                logger.warning("Keyword generation failed for %s on attempt %d/%d: %s", channel_name, attempt, max_attempts, exc)
        raise RuntimeError(f"Failed to generate keyword queries for {channel_name}") from last_error

    def _generate_subquery_items(self, *, channel_name: str, background: str, base_query: str, n_subqueries: int = DEFAULT_SUBQUERY_COUNT, max_attempts: int = 3) -> List[Dict[str, str]]:
        prompt = _CHANNEL_SUBQUERY_PROMPT.format(
            background=str(background or "")[:3500],
            base_query=base_query,
            n_subqueries=n_subqueries,
        )
        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                response = self.engine.generate(
                    content=prompt,
                    system_prompt="Return only valid JSON. Be specific to the background and base query.",
                    temperature=0.0,
                )
                validated = self._validate_subquery_payload(_extract_json(response))
                logger.info(
                    "Generated semantic subqueries for %s on attempt %d: %d subqueries",
                    channel_name,
                    attempt,
                    len(validated),
                )
                return validated
            except Exception as exc:
                last_error = exc
                logger.warning("Semantic subquery generation failed for %s on attempt %d/%d: %s", channel_name, attempt, max_attempts, exc)
        raise RuntimeError(f"Failed to generate semantic subqueries for {channel_name}") from last_error

    def _generate_channel_plan(self, *, channel_name: str, config: Config, background: str, base_query: str, n_subqueries: int = DEFAULT_SUBQUERY_COUNT, max_attempts: int = 3) -> Dict[str, Any]:
        pubmed_queries = self._generate_pubmed_queries(
            channel_name=channel_name,
            config=config,
            background=background,
            base_query=base_query,
            n_queries=self._pubmed_query_count(channel_name),
            max_attempts=max_attempts,
        )
        items = self._generate_subquery_items(
            channel_name=channel_name,
            background=background,
            base_query=base_query,
            n_subqueries=n_subqueries,
            max_attempts=max_attempts,
        )
        return {"pubmed_queries": pubmed_queries, "items": items}

    def _session_channel_dir(self, session_key: str, channel_name: str) -> Path:
        channel_dir = self.store.channel_documents_path(session_key, channel_name).parent
        channel_dir.mkdir(parents=True, exist_ok=True)
        return channel_dir

    def _summaries_path(self, session_key: str, channel_name: str) -> Path:
        return self._session_channel_dir(session_key, channel_name) / "paper_summaries.json"

    def _rankings_path(self, session_key: str, channel_name: str) -> Path:
        return self._session_channel_dir(session_key, channel_name) / "retrieval_debug.json"

    def _eligible_pmc_documents(self, documents: Iterable[RAGDocument]) -> List[RAGDocument]:
        candidates = self.store.deduplicate_documents(documents)
        candidates = candidates[:MAX_PMC_CANDIDATES_PER_CHANNEL]
        enriched_docs: List[RAGDocument] = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            future_map = {pool.submit(self._resolve_pmc_document, doc): doc for doc in candidates}
            for future in as_completed(future_map):
                resolved = future.result()
                if resolved is not None:
                    enriched_docs.append(resolved)
        enriched_docs = self.store.deduplicate_documents(enriched_docs)
        enriched_docs.sort(key=lambda doc: (str(doc.published or ""), doc.title), reverse=True)
        return enriched_docs

    def _resolve_pmc_document(self, base_document: RAGDocument) -> RAGDocument | None:
        cached = self.store.load_cached_core_document(base_document.doc_id)
        if cached is not None and cached.doc_type == "core_full_text" and cached.source == "pmc" and cached.sections:
            return cached
        try:
            enriched = fetch_core_document(base_document)
        except Exception as exc:
            logger.warning(
                "Skipping PMC full-text resolution for %s (%s) after fetch error: %s",
                base_document.doc_id,
                base_document.title,
                exc,
            )
            return None
        if enriched is None or not enriched.has_full_text or enriched.document.source != "pmc":
            return None
        core_doc = enriched.document
        core_doc.metadata = {
            **core_doc.metadata,
            "has_full_text": True,
            "extracted_methods": enriched.extracted_methods,
            "enrichment_source": enriched.enrichment_source,
        }
        self.store.save_cached_core_document(base_document.doc_id, core_doc)
        return core_doc

    def _load_or_fetch_channel_documents(self, *, session_key: str, channel_name: str, channel_plan: Dict[str, Any]) -> List[RAGDocument]:
        documents_path = self.store.channel_documents_path(session_key, channel_name)
        if documents_path.exists():
            cached_documents = self.store.deduplicate_documents(self.store.load_documents(documents_path))
            if cached_documents:
                print(
                    f"loaded cached {channel_name} papers: "
                    f"{len(cached_documents)} PMC full-text documents "
                    f"(session={session_key})"
                )
                for document in cached_documents:
                    self._paper_documents_by_id[document.doc_id] = document
                return cached_documents

        print(f"fetching {channel_name} papers with queries:")
        for idx, query in enumerate(channel_plan["pubmed_queries"], start=1):
            print(f"  {idx}. {query}")

        pubmed_documents = fetch_pubmed_documents(channel_plan["pubmed_queries"], MAX_PUBMED_RESULTS_PER_QUERY)
        print(f"retrieved {len(pubmed_documents)} PubMed candidate papers for {channel_name}")
        eligible_documents = self._eligible_pmc_documents(pubmed_documents)
        print(f"resolved {len(eligible_documents)} PMC full-text papers for {channel_name}")
        if not eligible_documents:
            raise RuntimeError(f"Runtime RAG produced no PMC full-text documents for {channel_name}")
        self.store.save_documents(documents_path, eligible_documents)
        for document in eligible_documents:
            self._paper_documents_by_id[document.doc_id] = document
        return eligible_documents

    def _ensure_channel_index(self, *, channel_name: str, config: Config, payload: Dict[str, Any], base_query: str, background: str) -> tuple[str, str, Dict[str, Any], Dict[str, RAGDocument]]:
        session_key = self._channel_hash(channel_name, payload, base_query, background)
        channel_dir = self._session_channel_dir(session_key, channel_name)
        plan_path = self.store.channel_keywords_path(session_key, channel_name)
        if plan_path.exists():
            with open(plan_path, "r", encoding="utf-8") as handle:
                channel_plan = self._validate_channel_plan(json.load(handle))
        else:
            channel_plan = self._generate_channel_plan(channel_name=channel_name, config=config, background=background, base_query=base_query)
            _json_dump(channel_plan, plan_path)

        print(f"semantic retrieval plan for {channel_name}:")
        for idx, item in enumerate(channel_plan["items"], start=1):
            print(f"  subquery {idx}: {item['subquery']}")
            print(f"  hyde abstract {idx}: {item['hyde_abstract']}")

        collection_name = self.store.runtime_collection_name(session_key, channel_name)
        documents = self._load_or_fetch_channel_documents(session_key=session_key, channel_name=channel_name, channel_plan=channel_plan)
        embedded_chunks = self.store.build_runtime_index(collection_name, documents, rebuild=True)
        print(
            f"embedded {embedded_chunks} section chunks from "
            f"{len(documents)} papers for {channel_name}"
        )
        documents_by_id = {document.doc_id: document for document in documents}
        self._channel_documents_by_collection[collection_name] = documents_by_id
        self._channel_cache_keys[(channel_name, base_query)] = session_key
        _ = channel_dir
        return session_key, collection_name, channel_plan, documents_by_id

    def _aggregate_hits_to_ranked_papers(self, hits: List[RAGHit], documents_by_id: Dict[str, RAGDocument]) -> List[Dict[str, Any]]:
        aggregated: Dict[str, Dict[str, Any]] = {}
        for rank, hit in enumerate(hits, start=1):
            document = documents_by_id.get(hit.doc_id)
            if document is None:
                continue
            entry = aggregated.setdefault(
                hit.doc_id,
                {
                    "paper_id": hit.doc_id,
                    "title": hit.title,
                    "source": hit.source,
                    "published": hit.published,
                    "url": hit.url,
                    "doc_type": hit.doc_type,
                    "score": 0.0,
                    "best_chunk_score": 0.0,
                    "best_section_type": hit.section_type,
                    "best_section_heading": hit.section_heading,
                    "best_snippet": hit.snippet,
                    "hit_count": 0,
                },
            )
            rank_score = _subquery_rank_score(rank, hit.score)
            entry["score"] += rank_score
            entry["hit_count"] += 1
            if float(hit.score or 0.0) >= float(entry["best_chunk_score"]):
                entry["best_chunk_score"] = float(hit.score or 0.0)
                entry["best_section_type"] = hit.section_type
                entry["best_section_heading"] = hit.section_heading
                entry["best_snippet"] = hit.snippet
        ranked = sorted(
            aggregated.values(),
            key=lambda item: (float(item["score"]), float(item["best_chunk_score"]), int(item["hit_count"])),
            reverse=True,
        )
        for idx, item in enumerate(ranked, start=1):
            item["rank"] = idx
        return ranked

    def _rrf_fuse(self, ranked_lists: List[List[Dict[str, Any]]], documents_by_id: Dict[str, RAGDocument], k: int = DEFAULT_RRF_K) -> List[PromotedPaper]:
        fused: Dict[str, Dict[str, Any]] = {}
        for ranked_list in ranked_lists:
            for rank, item in enumerate(ranked_list, start=1):
                paper_id = str(item.get("paper_id", "")).strip()
                if not paper_id:
                    continue
                document = documents_by_id.get(paper_id)
                if document is None:
                    continue
                entry = fused.setdefault(
                    paper_id,
                    {
                        "paper_id": paper_id,
                        "title": document.title,
                        "source": document.source,
                        "score": 0.0,
                        "reasons": [],
                    },
                )
                entry["score"] += 1.0 / float(k + rank)
                section_type = str(item.get("best_section_type", "")).strip() or "section"
                snippet = _shorten(str(item.get("best_snippet", "")).strip(), 180)
                entry["reasons"].append(f"{section_type}: {snippet}" if snippet else section_type)
        ordered = sorted(fused.values(), key=lambda item: float(item["score"]), reverse=True)
        return [
            PromotedPaper(
                doc_id=item["paper_id"],
                title=item["title"],
                source=item["source"],
                reason=" | ".join(item["reasons"][:3]) or "Retrieved across subqueries.",
                priority=idx + 1,
            )
            for idx, item in enumerate(ordered)
        ]

    def _generate_paper_summary(self, *, document: RAGDocument, session_key: str, channel_name: str) -> Dict[str, str]:
        cache_path = self._summaries_path(session_key, channel_name)
        cache: Dict[str, Any] = {}
        if cache_path.exists():
            try:
                cache = json.loads(cache_path.read_text(encoding="utf-8"))
            except Exception:
                cache = {}
        if isinstance(cache.get(document.doc_id), dict):
            return cache[document.doc_id]

        section_map = {section.section_type: section.text for section in document.sections}
        prompt = _PAPER_SUMMARY_PROMPT.format(
            title=document.title,
            published=document.published or "unknown",
            abstract=_shorten(section_map.get("abstract", document.abstract), 2500),
            methods=_shorten(section_map.get("methods", ""), 3000),
            results=_shorten(section_map.get("results", ""), 3000),
            discussion=_shorten(section_map.get("discussion", ""), 2500),
        )
        response = self.engine.generate(
            content=prompt,
            system_prompt="Return only valid JSON. Be concise, factual, and grounded in the supplied paper text.",
            temperature=0.0,
        )
        payload = _extract_json(response)
        if not isinstance(payload, dict):
            raise ValueError(f"Invalid paper summary payload for {document.doc_id}")
        summary = {
            "objective": _shorten(str(payload.get("objective", "")).strip(), 500),
            "key_methods": _shorten(str(payload.get("key_methods", "")).strip(), 600),
            "main_findings": _shorten(str(payload.get("main_findings", "")).strip(), 600),
            "limitations": _shorten(str(payload.get("limitations", "")).strip(), 500),
        }
        cache[document.doc_id] = summary
        _json_dump(cache, cache_path)
        return summary

    def _format_summary_context(self, *, channel_name: str, documents: List[RAGDocument], session_key: str) -> str:
        label = CHANNEL_LABELS.get(channel_name, channel_name.upper())
        if not documents:
            return f"{label}\n<none>"
        lines = [
            label,
            "Tool contract: fetch_paper_section(paper_id, section_type)",
        ]
        for idx, document in enumerate(documents[:DEFAULT_CHANNEL_TOP_K], start=1):
            summary = self._generate_paper_summary(document=document, session_key=session_key, channel_name=channel_name)
            available_sections = sorted({section.section_type for section in document.sections if section.section_type})
            lines.extend(
                [
                    f"{idx}. [PMC] {document.title} ({document.published or 'unknown date'})",
                    f"   paper_id={document.doc_id}",
                    f"   sections={', '.join(available_sections) or '<none>'}",
                    f"   Objective: {summary['objective'] or '<none>'}",
                    f"   Key methods: {summary['key_methods'] or '<none>'}",
                    f"   Main findings: {summary['main_findings'] or '<none>'}",
                    f"   Limitations: {summary['limitations'] or '<none>'}",
                    f"   url={document.url or '<none>'}",
                ]
            )
        return "\n".join(lines)

    def _channel_documents(self, *, channel_name: str, config: Config, payload: Dict[str, Any], base_query: str, background: str, keep: int = DEFAULT_CHANNEL_TOP_K) -> List[RAGDocument]:
        cache_key = json.dumps(
            {
                "channel_name": channel_name,
                "payload": payload,
                "base_query": base_query,
                "background": background,
                "keep": keep,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        prepared = self._prepared_channel_contexts.get(cache_key)
        if isinstance(prepared, dict) and isinstance(prepared.get("documents"), list):
            return list(prepared["documents"])

        session_key, collection_name, channel_plan, documents_by_id = self._ensure_channel_index(
            channel_name=channel_name,
            config=config,
            payload=payload,
            base_query=base_query,
            background=background,
        )
        subquery_rankings: List[List[Dict[str, Any]]] = []
        ranking_debug: Dict[str, Any] = {
            "base_query": base_query,
            "pubmed_queries": list(channel_plan["pubmed_queries"]),
            "items": [],
            "final_rrf": [],
        }

        for item in channel_plan["items"]:
            hits = self.store.search_runtime(collection_name, item["hyde_abstract"], n_results=DEFAULT_CHANNEL_SEARCH_HITS)
            ranked_papers = self._aggregate_hits_to_ranked_papers(hits, documents_by_id)
            subquery_rankings.append(ranked_papers)
            ranking_debug["items"].append(
                {
                    "subquery": item["subquery"],
                    "hyde_abstract": item["hyde_abstract"],
                    "paper_ranking": ranked_papers[:15],
                }
            )

        fused = self._rrf_fuse(subquery_rankings, documents_by_id)
        selected_docs: List[RAGDocument] = []
        for promoted in fused:
            document = documents_by_id.get(promoted.doc_id)
            if document is None:
                continue
            document.metadata = {**document.metadata, "selection_reason": promoted.reason}
            selected_docs.append(document)
            if len(selected_docs) >= keep:
                break

        ranking_debug["final_rrf"] = [
            {
                "paper_id": promoted.doc_id,
                "title": promoted.title,
                "reason": promoted.reason,
                "priority": promoted.priority,
            }
            for promoted in fused[: max(keep, 10)]
        ]
        ranking_debug["dedup_policy"] = "PMID/DOI/normalized_title early and late"
        _json_dump(ranking_debug, self._rankings_path(session_key, channel_name))
        self._prepared_channel_contexts[cache_key] = {
            "documents": list(selected_docs),
            "session_key": session_key,
            "channel_name": channel_name,
            "payload": payload,
            "base_query": base_query,
            "background": background,
            "keep": keep,
        }
        return selected_docs

    def fetch_paper_section(self, paper_id: str, section_type: str) -> Dict[str, Any]:
        normalized_type = normalize_section_type(section_type)
        document = self._paper_documents_by_id.get(paper_id)
        if document is None:
            raise KeyError(f"Unknown paper_id: {paper_id}")
        for section in document.sections:
            if section.section_type == normalized_type:
                payload: Dict[str, Any] = {
                    "paper_id": document.doc_id,
                    "title": document.title,
                    "section_type": section.section_type,
                    "section_heading": section.heading,
                    "text": section.text,
                }
                if len(section.text) > 4000:
                    payload["chunks"] = self.store._chunk_text(section.text, chunk_size=1800, overlap=150)
                return payload
        raise KeyError(f"Section {normalized_type} not available for paper_id={paper_id}")

    def _document_hits(self, documents: Iterable[RAGDocument]) -> List[RAGHit]:
        hits: List[RAGHit] = []
        for document in documents:
            snippet = _shorten(document.abstract or document.text or "", 320)
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

    def _dataset_channel(self, config: Config, background: str) -> List[RAGDocument]:
        payload = {
            "feat_stats": str(config.feat_stats or ""),
            "background": str(background or ""),
        }
        base_query = self._resolve_base_query("dataset", config, background)
        return self._channel_documents(channel_name="dataset", config=config, payload=payload, base_query=base_query, background=background)

    def _prior_resource_channel(self, config: Config, background: str) -> List[RAGDocument]:
        payload = {
            "prior_resource_summary": str(config.prior_resource_summary or ""),
            "feat_stats": str(config.feat_stats or ""),
            "resource_names": self._prior_resource_names(config),
        }
        base_query = self._resolve_base_query("prior_resources", config, background)
        return self._channel_documents(channel_name="prior_resources", config=config, payload=payload, base_query=base_query, background=background)

    def _prior_method_channel(self, config: Config, background: str) -> List[RAGDocument]:
        payload = {
            "prior_resource_summary": str(config.prior_resource_summary or ""),
            "feat_stats": str(config.feat_stats or ""),
            "metrics": str(config.metrics or ""),
            "prior_resource_types": self._prior_resource_types(config),
        }
        base_query = self._resolve_base_query("prior_methods", config, background)
        return self._channel_documents(channel_name="prior_methods", config=config, payload=payload, base_query=base_query, background=background)

    def _benchmark_channel(self, config: Config, background: str) -> List[RAGDocument]:
        payload = {
            "feat_stats": str(config.feat_stats or ""),
            "background": str(background or ""),
        }
        base_query = self._resolve_base_query("benchmark", config, background)
        return self._channel_documents(channel_name="benchmark", config=config, payload=payload, base_query=base_query, background=background)

    def prepare_contexts(self, config: Config, background: str) -> Dict[str, Any]:
        dataset_documents = self._dataset_channel(config, background)
        prior_resource_documents = self._prior_resource_channel(config, background)
        prior_method_documents = self._prior_method_channel(config, background)
        benchmark_documents = self._benchmark_channel(config, background)

        dataset_base_query = self._resolve_base_query("dataset", config, background)
        dataset_session_key = self._channel_hash(
            "dataset",
            {"feat_stats": str(config.feat_stats or ""), "background": str(background or "")},
            dataset_base_query,
            background,
        )
        prior_resource_base_query = self._resolve_base_query("prior_resources", config, background)
        prior_resource_session_key = self._channel_hash(
            "prior_resources",
            {"prior_resource_summary": str(config.prior_resource_summary or ""), "feat_stats": str(config.feat_stats or ""), "resource_names": self._prior_resource_names(config)},
            prior_resource_base_query,
            background,
        )
        prior_method_base_query = self._resolve_base_query("prior_methods", config, background)
        prior_method_session_key = self._channel_hash(
            "prior_methods",
            {
                "prior_resource_summary": str(config.prior_resource_summary or ""),
                "feat_stats": str(config.feat_stats or ""),
                "metrics": str(config.metrics or ""),
                "prior_resource_types": self._prior_resource_types(config),
            },
            prior_method_base_query,
            background,
        )
        benchmark_base_query = self._resolve_base_query("benchmark", config, background)
        benchmark_session_key = self._channel_hash(
            "benchmark",
            {"feat_stats": str(config.feat_stats or ""), "background": str(background or "")},
            benchmark_base_query,
            background,
        )

        prepared = {
            "dataset": {
                "documents": list(dataset_documents),
                "context": self._format_summary_context(channel_name="dataset", documents=dataset_documents, session_key=dataset_session_key),
                "hits": self._document_hits(dataset_documents),
                "session_key": dataset_session_key,
                "collection_name": self.store.runtime_collection_name(dataset_session_key, "dataset"),
            },
            "prior_resources": {
                "documents": list(prior_resource_documents),
                "context": self._format_summary_context(channel_name="prior_resources", documents=prior_resource_documents, session_key=prior_resource_session_key),
                "hits": self._document_hits(prior_resource_documents),
                "session_key": prior_resource_session_key,
                "collection_name": self.store.runtime_collection_name(prior_resource_session_key, "prior_resources"),
            },
            "prior_methods": {
                "documents": list(prior_method_documents),
                "context": self._format_summary_context(channel_name="prior_methods", documents=prior_method_documents, session_key=prior_method_session_key),
                "hits": self._document_hits(prior_method_documents),
                "session_key": prior_method_session_key,
                "collection_name": self.store.runtime_collection_name(prior_method_session_key, "prior_methods"),
            },
            "benchmark": {
                "documents": list(benchmark_documents),
                "context": self._format_summary_context(channel_name="benchmark", documents=benchmark_documents, session_key=benchmark_session_key),
                "hits": self._document_hits(benchmark_documents),
                "session_key": benchmark_session_key,
                "collection_name": self.store.runtime_collection_name(benchmark_session_key, "benchmark"),
            },
        }
        self._prepared_channel_contexts["__prepared_contexts__"] = prepared
        return prepared

    def _prepared_contexts(self) -> Dict[str, Any]:
        prepared = self._prepared_channel_contexts.get("__prepared_contexts__")
        if not isinstance(prepared, dict):
            raise RuntimeError("RAG contexts have not been prepared. Call prepare_contexts(...) first.")
        return prepared

    @staticmethod
    def load_marker_db_context(config: Config) -> str:
        datasets_dir = Path(config.cur_path) / "Datasets"
        if not datasets_dir.is_dir():
            return "(no marker databases available)"

        sections: List[str] = []
        db_files = {
            "Cell_marker_Human.xlsx": "CellMarker database — human cell type marker genes by tissue",
            "GO_terms.csv": "Gene Ontology — gene-biological process annotations",
            "MsigDB.csv": "Molecular Signatures Database — pathway gene sets",
            "NeST.tsv": "NeST — gene regulatory network / transcription factor targets",
        }
        for filename, description in db_files.items():
            path = datasets_dir / filename
            if path.exists():
                size_kb = path.stat().st_size / 1024
                sections.append(f"- {filename} ({size_kb:.0f} KB): {description}")

        gene_emb_dir = datasets_dir / "gene_embedding"
        if gene_emb_dir.is_dir():
            sections.append("- gene_embedding/: Pre-computed gene text embeddings from NCBI descriptions")

        meta_path = datasets_dir / "meta_info.csv"
        if meta_path.exists():
            try:
                import csv
                with open(meta_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    resource_types = set()
                    for row in reader:
                        rt = str(row.get("resource_type", "")).strip()
                        if rt:
                            resource_types.add(rt)
                    if resource_types:
                        sections.append(f"- meta_info.csv: Prior resource metadata covering: {', '.join(sorted(resource_types))}")
            except Exception:
                sections.append("- meta_info.csv: Prior resource metadata")

        if not sections:
            return "(no marker databases available)"
        return "Available structured databases:\n" + "\n".join(sections)
