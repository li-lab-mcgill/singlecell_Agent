from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List


def normalize_title(text: str) -> str:
    return re.sub(r"\W+", " ", str(text or "").lower()).strip()


def dedup_key(doc_id: str, doi: str, title: str) -> tuple[str, str, str]:
    return (str(doc_id or "").strip(), str(doi or "").lower().strip(), normalize_title(title))


@dataclass
class RAGSection:
    section_id: str
    section_type: str
    heading: str
    text: str
    order: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_id": self.section_id,
            "section_type": self.section_type,
            "heading": self.heading,
            "text": self.text,
            "order": self.order,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "RAGSection":
        return cls(
            section_id=str(payload.get("section_id", "")),
            section_type=str(payload.get("section_type", "")),
            heading=str(payload.get("heading", "")),
            text=str(payload.get("text", "")),
            order=int(payload.get("order", 0) or 0),
            metadata=payload.get("metadata", {}) if isinstance(payload.get("metadata", {}), dict) else {},
        )


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
    sections: List[RAGSection] = field(default_factory=list)

    def searchable_text(self) -> str:
        if self.sections:
            pieces: List[str] = []
            for section in self.sections:
                if str(section.heading).strip():
                    pieces.append(section.heading)
                if str(section.text).strip():
                    pieces.append(section.text)
            primary_text = "\n\n".join(pieces)
        else:
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
            "sections": [section.to_dict() for section in self.sections],
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
            sections=[
                RAGSection.from_dict(item)
                for item in payload.get("sections", [])
                if isinstance(item, dict)
            ],
        )


@dataclass
class RAGChunk:
    chunk_id: str
    doc_id: str
    source: str
    title: str
    text: str
    doc_type: str
    section_type: str = ""
    section_heading: str = ""
    chunk_index: int = 0
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
    is_runtime_fallback: bool = False
    chunk_id: str = ""
    section_type: str = ""
    section_heading: str = ""
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
    dataset_context: str
    prior_resource_context: str
    prior_method_context: str
    model_design_context: str
    dataset_hits: List[RAGHit] = field(default_factory=list)
    prior_resource_hits: List[RAGHit] = field(default_factory=list)
    prior_method_hits: List[RAGHit] = field(default_factory=list)
    model_design_hits: List[RAGHit] = field(default_factory=list)
