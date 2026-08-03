from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from backend.context_access import (
    check_prior_coverage as context_check_prior_coverage,
    query_marker_database as context_query_marker_database,
    query_pathway_database as context_query_pathway_database,
    read_dataset_summary as context_read_dataset_summary,
    read_label_distribution as context_read_label_distribution,
    read_prior_resource_summary as context_read_prior_resource_summary,
)
from rag.types import RAGDocument


def _safe_json_load(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


class PaperBackend:
    def __init__(self, *, rag_agent: Any, config: Any, prepared_contexts: Dict[str, Any]):
        self.rag_agent = rag_agent
        self.config = config
        self.prepared_contexts = prepared_contexts
        self._documents_by_id: Dict[str, RAGDocument] = {}
        self._doc_channel: Dict[str, str] = {}
        self._paper_summaries: Dict[str, Dict[str, str]] = {}

        for channel_name, payload in prepared_contexts.items():
            if not isinstance(payload, dict):
                continue
            session_key = str(payload.get("session_key", "")).strip()
            if session_key:
                summary_cache = _safe_json_load(rag_agent._summaries_path(session_key, channel_name))
                for doc_id, summary in summary_cache.items():
                    if isinstance(summary, dict):
                        self._paper_summaries[doc_id] = {
                            "objective": str(summary.get("objective", "")).strip(),
                            "method_and_dataset": str(summary.get("method_and_dataset", "")).strip(),
                            "key_methods": str(summary.get("key_methods", "")).strip(),
                            "benchmark_methods": str(summary.get("benchmark_methods", "")).strip(),
                            "main_findings": str(summary.get("main_findings", "")).strip(),
                            "limitations": str(summary.get("limitations", "")).strip(),
                            "figure_captions": str(summary.get("figure_captions", "")).strip(),
                        }
            for document in payload.get("documents", []):
                if isinstance(document, RAGDocument):
                    self._documents_by_id[document.doc_id] = document
                    self._doc_channel[document.doc_id] = channel_name

    def read_dataset_summary(self) -> Dict[str, Any]:
        return context_read_dataset_summary(self.config)

    def read_label_distribution(self, label_key: str) -> Dict[str, Any]:
        return context_read_label_distribution(self.config, label_key)

    def read_prior_resource_summary(self) -> Dict[str, Any]:
        return context_read_prior_resource_summary(self.config)

    def check_prior_coverage(self, resource_name: str) -> Dict[str, Any]:
        return context_check_prior_coverage(self.config, resource_name)

    def search_index(self, query: str, channel: str, top_k: int = 5) -> Dict[str, Any]:
        channel_name = str(channel or "").strip()
        if channel_name not in self.prepared_contexts:
            raise ValueError(f"Unsupported channel: {channel_name}")
        collection_name = str(self.prepared_contexts[channel_name].get("collection_name", "")).strip()
        hits = self.rag_agent.store.search_runtime(collection_name, str(query or "").strip(), n_results=max(1, int(top_k)))
        results: List[Dict[str, Any]] = []
        for hit in hits[: max(1, int(top_k))]:
            results.append(
                {
                    "paper_id": hit.doc_id,
                    "title": hit.title,
                    "score": float(hit.score),
                    "section_type": hit.section_type or "",
                    "snippet": hit.snippet,
                    "url": hit.url,
                }
            )
        return {"channel": channel_name, "query": query, "results": results}

    def read_paper_summary(self, paper_id: str) -> Dict[str, Any]:
        doc_id = str(paper_id or "").strip()
        document = self._documents_by_id.get(doc_id)
        if document is None:
            raise ValueError(f"Unknown paper_id: {doc_id}")
        summary = self._paper_summaries.get(doc_id)
        if summary is None:
            channel_name = self._doc_channel.get(doc_id, "dataset")
            session_key = str(self.prepared_contexts.get(channel_name, {}).get("session_key", "")).strip()
            summary = self.rag_agent._generate_paper_summary(document=document, session_key=session_key, channel_name=channel_name)
            self._paper_summaries[doc_id] = summary
        return {
            "paper_id": doc_id,
            "title": document.title,
            "channel": self._doc_channel.get(doc_id, ""),
            "summary": summary,
        }

    def fetch_paper_section(self, paper_id: str, section_type: str, top_n_chunks: int = 3) -> Dict[str, Any]:
        payload = self.rag_agent.fetch_paper_section(paper_id, section_type)
        chunks = payload.get("chunks")
        if isinstance(chunks, list):
            payload["chunks"] = chunks[: max(1, int(top_n_chunks))]
        return payload

    def query_marker_database(self, tissue: str, species: str) -> Dict[str, Any]:
        return context_query_marker_database(self.config, tissue, species)

    def query_pathway_database(self, database: str, gene: str) -> Dict[str, Any]:
        return context_query_pathway_database(self.config, database, gene)
