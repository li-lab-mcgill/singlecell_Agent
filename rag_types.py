from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class RAGDocument:
    doc_id: str
    source: str
    source_id: str
    title: str
    text: str
    abstract: str = ""
    url: str = ""
    authors: str = ""
    published: str = ""
    doi: str = ""
    doc_type: str = "general"
    categories: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def searchable_text(self) -> str:
        primary_text = self.text or self.abstract
        return "\n\n".join(part for part in [self.title, primary_text] if str(part).strip())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "source": self.source,
            "source_id": self.source_id,
            "title": self.title,
            "text": self.text,
            "abstract": self.abstract,
            "url": self.url,
            "authors": self.authors,
            "published": self.published,
            "doi": self.doi,
            "doc_type": self.doc_type,
            "categories": list(self.categories),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "RAGDocument":
        return cls(
            doc_id=str(payload.get("doc_id", "")),
            source=str(payload.get("source", "")),
            source_id=str(payload.get("source_id", "")),
            title=str(payload.get("title", "")),
            text=str(payload.get("text", "")),
            abstract=str(payload.get("abstract", "")),
            url=str(payload.get("url", "")),
            authors=str(payload.get("authors", "")),
            published=str(payload.get("published", "")),
            doi=str(payload.get("doi", "")),
            doc_type=str(payload.get("doc_type", "general")),
            categories=[str(item) for item in payload.get("categories", []) if str(item).strip()],
            metadata=payload.get("metadata", {}) if isinstance(payload.get("metadata", {}), dict) else {},
        )


@dataclass
class RAGChunk:
    chunk_id: str
    doc_id: str
    source: str
    title: str
    text: str
    doc_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RAGHit:
    doc_id: str
    title: str
    source: str
    score: float
    snippet: str
    url: str
    doc_type: str
    source_id: str = ""
    published: str = ""
    doi: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PromotedPaper:
    doc_id: str
    title: str
    source: str
    reason: str
    priority: int


@dataclass
class CoreFetchResult:
    document: RAGDocument
    enrichment_source: str
    has_full_text: bool
    extracted_methods: bool


@dataclass
class ConsultantRAGContext:
    query_text: str
    general_context: str
    core_context: str
    general_hits: List[RAGHit] = field(default_factory=list)
    core_hits: List[RAGHit] = field(default_factory=list)
    promoted_papers: List[PromotedPaper] = field(default_factory=list)
