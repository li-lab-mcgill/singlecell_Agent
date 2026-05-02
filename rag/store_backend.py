from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from datetime import datetime

from rag.types import RAGChunk, RAGDocument, RAGHit, RAGSection, dedup_key

try:
    import chromadb
except ImportError:  # pragma: no cover - runtime dependency guard
    chromadb = None

try:
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
except ImportError:  # pragma: no cover - runtime dependency guard
    SentenceTransformerEmbeddingFunction = None

try:
    from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
except ImportError:  # pragma: no cover - runtime dependency guard
    OpenAIEmbeddingFunction = None


GENERAL_COLLECTION = "general_knowledge_base"
CORE_COLLECTION = "core_knowledge_base"
SESSION_GENERAL_COLLECTION = "runtime_session_knowledge_base"
DEFAULT_LOCAL_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DEFAULT_OPENAI_EMBEDDING_MODEL = "text-embedding-3-large"

_MONTH_BY_ABBR = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

def _to_chroma_metadata(payload: Dict[str, object]) -> Dict[str, object]:
    converted: Dict[str, object] = {}
    for key, value in payload.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            converted[key] = value
        elif isinstance(value, list):
            converted[key] = "; ".join(str(item) for item in value if str(item).strip())
        elif isinstance(value, dict):
            converted[key] = json.dumps(value, ensure_ascii=False, sort_keys=True)
        else:
            converted[key] = str(value)
    return converted


def _publication_metadata(published: str) -> Dict[str, object]:
    text = str(published or "").strip()
    if not text:
        return {}

    year_match = re.search(r"\b(19|20)\d{2}\b", text)
    if not year_match:
        return {}

    year = int(year_match.group(0))
    metadata: Dict[str, object] = {"publication_year": year}

    normalized_text = re.sub(r"\s+", " ", text).strip()
    direct_formats = [
        ("%Y-%m-%d", "publication_date_iso"),
        ("%Y/%m/%d", "publication_date_iso"),
    ]
    for fmt, key in direct_formats:
        try:
            metadata[key] = datetime.strptime(normalized_text, fmt).strftime("%Y-%m-%d")
            return metadata
        except ValueError:
            continue

    year_first_match = re.search(
        r"\b((19|20)\d{2})\b\s+([A-Za-z]{3,9})(?:\s+(\d{1,2}))?\b",
        normalized_text,
        flags=re.IGNORECASE,
    )
    month_first_match = re.search(
        r"\b([A-Za-z]{3,9})\s+(\d{1,2})?,?\s*((19|20)\d{2})\b",
        normalized_text,
        flags=re.IGNORECASE,
    )
    month = None
    day = None
    if year_first_match:
        month = _MONTH_BY_ABBR.get(year_first_match.group(3)[:3].lower())
        day_token = year_first_match.group(4)
        if day_token:
            parsed_day = int(day_token)
            if 1 <= parsed_day <= 31:
                day = parsed_day
    elif month_first_match:
        month = _MONTH_BY_ABBR.get(month_first_match.group(1)[:3].lower())
        day_token = month_first_match.group(2)
        if day_token:
            parsed_day = int(day_token)
            if 1 <= parsed_day <= 31:
                day = parsed_day

    if month is not None:
        metadata["publication_month"] = month
        if day is not None:
            metadata["publication_day"] = day
            metadata["publication_date_iso"] = f"{year:04d}-{month:02d}-{day:02d}"
        else:
            metadata["publication_date_iso"] = f"{year:04d}-{month:02d}"
    return metadata


class RAGStore:
    def __init__(
        self,
        root_dir: str | Path,
        embedding_model: Optional[str] = None,
        embedding_backend: str = "local",
    ):
        if chromadb is None:
            raise RuntimeError("RAG support requires chromadb. Install it before running default.py.")
        self.root_dir = Path(root_dir)
        self.raw_dir = self.root_dir / "raw"
        self.processed_dir = self.root_dir / "processed"
        self.sessions_dir = self.root_dir / "sessions"
        self.cache_dir = self.root_dir / "cache"
        self.chroma_dir = self.root_dir / "chroma"
        for directory in [self.raw_dir, self.processed_dir, self.sessions_dir, self.cache_dir, self.chroma_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        self.embedding_backend = str(embedding_backend or "local").strip().lower()
        if self.embedding_backend not in {"local", "openai"}:
            raise ValueError(f"Unsupported embedding backend: {embedding_backend}")
        self.embedding_model = embedding_model or (
            DEFAULT_OPENAI_EMBEDDING_MODEL if self.embedding_backend == "openai" else DEFAULT_LOCAL_EMBEDDING_MODEL
        )
        self.client = chromadb.PersistentClient(path=str(self.chroma_dir))
        if self.embedding_backend == "openai":
            if OpenAIEmbeddingFunction is None:
                raise RuntimeError("RAG OpenAI embeddings require chromadb with OpenAI embedding support installed.")
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            if not api_key:
                raise RuntimeError("Missing required environment variable: OPENAI_API_KEY")
            self.embedding_function = OpenAIEmbeddingFunction(api_key=api_key, model_name=self.embedding_model)
        else:
            if SentenceTransformerEmbeddingFunction is None:
                raise RuntimeError("RAG local embeddings require sentence-transformers to be installed.")
            self.embedding_function = SentenceTransformerEmbeddingFunction(model_name=self.embedding_model)

    @property
    def general_corpus_path(self) -> Path:
        return self.processed_dir / "general_documents.json"

    @property
    def manifest_path(self) -> Path:
        return self.processed_dir / "build_manifest.json"

    def load_manifest(self) -> Dict[str, object]:
        if not self.manifest_path.exists():
            return {}
        with open(self.manifest_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload if isinstance(payload, dict) else {}

    def reset_runtime_artifacts(self) -> None:
        for directory in [self.sessions_dir, self.cache_dir]:
            if directory.exists():
                shutil.rmtree(directory, ignore_errors=True)
            directory.mkdir(parents=True, exist_ok=True)

    def core_cache_path(self, cache_key: str) -> Path:
        safe_name = re.sub(r"[^a-zA-Z0-9_.:-]+", "_", cache_key)
        return self.cache_dir / f"{safe_name}.json"

    def session_dir(self, session_key: str) -> Path:
        safe_name = re.sub(r"[^a-zA-Z0-9_.:-]+", "_", session_key)
        path = self.sessions_dir / safe_name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def session_documents_path(self, session_key: str) -> Path:
        return self.session_dir(session_key) / "documents.json"

    def channel_documents_path(self, session_key: str, channel_name: str) -> Path:
        safe_channel = re.sub(r"[^a-zA-Z0-9_.:-]+", "_", channel_name)
        return self.session_dir(session_key) / safe_channel / "documents.json"

    def channel_keywords_path(self, session_key: str, channel_name: str) -> Path:
        safe_channel = re.sub(r"[^a-zA-Z0-9_.:-]+", "_", channel_name)
        return self.session_dir(session_key) / safe_channel / "keywords.json"

    def runtime_collection_name(self, session_key: str, channel_name: str) -> str:
        safe_channel = re.sub(r"[^a-zA-Z0-9_.:-]+", "_", channel_name).lower()
        safe_session = re.sub(r"[^a-zA-Z0-9_.:-]+", "_", session_key).lower()
        return f"runtime_{safe_session}_{safe_channel}"[:63]

    def save_documents(self, path: Path, documents: Iterable[RAGDocument]) -> None:
        payload = [document.to_dict() for document in documents]
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def load_documents(self, path: Path) -> List[RAGDocument]:
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return [RAGDocument.from_dict(item) for item in payload if isinstance(item, dict)]

    def load_general_documents(self) -> Dict[str, RAGDocument]:
        return {document.doc_id: document for document in self.load_documents(self.general_corpus_path)}

    def load_cached_core_document(self, cache_key: str) -> Optional[RAGDocument]:
        cache_path = self.core_cache_path(cache_key)
        if not cache_path.exists():
            return None
        with open(cache_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return RAGDocument.from_dict(payload) if isinstance(payload, dict) else None

    def save_cached_core_document(self, cache_key: str, document: RAGDocument) -> None:
        cache_path = self.core_cache_path(cache_key)
        with open(cache_path, "w", encoding="utf-8") as handle:
            json.dump(document.to_dict(), handle, ensure_ascii=False, indent=2)

    def deduplicate_documents(self, documents: Iterable[RAGDocument]) -> List[RAGDocument]:
        deduped: List[RAGDocument] = []
        seen_keys = set()
        for document in documents:
            key = dedup_key(document.doc_id, document.doi, document.title)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            deduped.append(document)
        return deduped

    def _get_or_create_collection(self, name: str):
        return self.client.get_or_create_collection(name=name, embedding_function=self.embedding_function)

    def _reset_collection(self, name: str) -> None:
        try:
            self.client.delete_collection(name=name)
        except Exception:
            pass

    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        def split_long_paragraph(paragraph: str) -> List[str]:
            pieces: List[str] = []
            remaining = paragraph.strip()
            while len(remaining) > chunk_size:
                cut = remaining[:chunk_size].rfind(" ")
                if cut <= chunk_size // 2:
                    cut = chunk_size
                pieces.append(remaining[:cut].strip())
                start = cut
                if overlap > 0 and cut > overlap:
                    start = cut - overlap
                remaining = remaining[start:].strip()
            if remaining:
                pieces.append(remaining)
            return pieces

        paragraphs = [part.strip() for part in re.split(r"\n{2,}", text or "") if part.strip()]
        if not paragraphs:
            cleaned = re.sub(r"\s+", " ", text or "").strip()
            return [cleaned] if cleaned else []
        chunks: List[str] = []
        current = ""
        for paragraph in paragraphs:
            for part in split_long_paragraph(paragraph):
                candidate = part if not current else f"{current}\n\n{part}"
                if len(candidate) <= chunk_size:
                    current = candidate
                    continue
                if current:
                    chunks.append(current)
                    tail = current[-overlap:] if overlap > 0 else ""
                    merged = f"{tail}\n\n{part}".strip() if tail else part
                    current = merged if len(merged) <= chunk_size else part
                else:
                    current = part
        if current:
            chunks.append(current)
        return chunks

    def _upsert_batches(self, collection, *, ids: List[str], documents: List[str], metadatas: List[Dict[str, object]], batch_size: int = 500) -> None:
        for start in range(0, len(ids), batch_size):
            end = start + batch_size
            collection.upsert(ids=ids[start:end], documents=documents[start:end], metadatas=metadatas[start:end])

    def _chunk_document(self, document: RAGDocument) -> List[RAGChunk]:
        chunk_size = 1500 if document.doc_type.startswith("core") else 900
        overlap = 200 if document.doc_type.startswith("core") else 120
        sections = list(document.sections)
        if not sections:
            sections = [
                RAGSection(
                    section_id="body:0",
                    section_type="supplement",
                    heading=document.title or "Document",
                    text=document.searchable_text(),
                    order=0,
                    metadata={},
                )
            ]

        all_chunks: List[RAGChunk] = []
        for section in sections:
            section_chunks = self._chunk_text(section.text, chunk_size=chunk_size, overlap=overlap)
            for idx, chunk in enumerate(section_chunks):
                all_chunks.append(
                    RAGChunk(
                        chunk_id=f"{document.doc_id}::section::{section.section_id}::chunk::{idx}",
                        doc_id=document.doc_id,
                        source=document.source,
                        title=document.title,
                        text=chunk,
                        doc_type=document.doc_type,
                        section_type=section.section_type,
                        section_heading=section.heading,
                        chunk_index=idx,
                        metadata={**dict(document.metadata), **dict(section.metadata)},
                    )
                )
        return all_chunks

    def build_general_index(self, documents: Iterable[RAGDocument], rebuild: bool = False) -> int:
        if rebuild:
            self._reset_collection(GENERAL_COLLECTION)
        collection = self._get_or_create_collection(GENERAL_COLLECTION)
        chunk_ids: List[str] = []
        chunk_texts: List[str] = []
        metadatas: List[Dict[str, object]] = []
        for document in documents:
            for chunk in self._chunk_document(document):
                chunk_ids.append(chunk.chunk_id)
                chunk_texts.append(chunk.text)
                metadatas.append(
                    _to_chroma_metadata(
                        {
                            "doc_id": chunk.doc_id,
                            "source": chunk.source,
                            "source_id": document.source_id,
                            "title": chunk.title,
                            "url": document.url,
                            "doc_type": chunk.doc_type,
                            "chunk_id": chunk.chunk_id,
                            "paper_id": document.doc_id,
                            "section_type": chunk.section_type,
                            "section_heading": chunk.section_heading,
                            "chunk_index": chunk.chunk_index,
                            "published": document.published,
                            "doi": document.doi,
                            **_publication_metadata(document.published),
                            **chunk.metadata,
                        }
                    )
                )
        if chunk_ids:
            self._upsert_batches(collection, ids=chunk_ids, documents=chunk_texts, metadatas=metadatas)
        return len(chunk_ids)

    def build_runtime_index(self, collection_name: str, documents: Iterable[RAGDocument], rebuild: bool = True) -> int:
        if rebuild:
            self._reset_collection(collection_name)
        collection = self._get_or_create_collection(collection_name)
        chunk_ids: List[str] = []
        chunk_texts: List[str] = []
        metadatas: List[Dict[str, object]] = []
        for document in documents:
            for chunk in self._chunk_document(document):
                chunk_ids.append(chunk.chunk_id)
                chunk_texts.append(chunk.text)
                metadatas.append(
                    _to_chroma_metadata(
                        {
                            "doc_id": chunk.doc_id,
                            "source": chunk.source,
                            "source_id": document.source_id,
                            "title": chunk.title,
                            "url": document.url,
                            "doc_type": chunk.doc_type,
                            "chunk_id": chunk.chunk_id,
                            "paper_id": document.doc_id,
                            "section_type": chunk.section_type,
                            "section_heading": chunk.section_heading,
                            "chunk_index": chunk.chunk_index,
                            "published": document.published,
                            "doi": document.doi,
                            **_publication_metadata(document.published),
                            **chunk.metadata,
                        }
                    )
                )
        if chunk_ids:
            self._upsert_batches(collection, ids=chunk_ids, documents=chunk_texts, metadatas=metadatas)
        return len(chunk_ids)

    def build_session_index(self, documents: Iterable[RAGDocument], rebuild: bool = True) -> int:
        return self.build_runtime_index(SESSION_GENERAL_COLLECTION, documents, rebuild=rebuild)

    def upsert_core_documents(self, documents: Iterable[RAGDocument], consultant_type: str, query_hash: str) -> int:
        collection = self._get_or_create_collection(CORE_COLLECTION)
        chunk_ids: List[str] = []
        chunk_texts: List[str] = []
        metadatas: List[Dict[str, object]] = []
        for document in documents:
            for chunk in self._chunk_document(document):
                chunk_ids.append(f"{consultant_type}:{query_hash}:{chunk.chunk_id}")
                chunk_texts.append(chunk.text)
                metadatas.append(
                    _to_chroma_metadata(
                        {
                            "doc_id": document.doc_id,
                            "source": document.source,
                            "source_id": document.source_id,
                            "title": document.title,
                            "url": document.url,
                            "doc_type": document.doc_type,
                            "chunk_id": chunk.chunk_id,
                            "paper_id": document.doc_id,
                            "section_type": chunk.section_type,
                            "section_heading": chunk.section_heading,
                            "chunk_index": chunk.chunk_index,
                            "published": document.published,
                            "doi": document.doi,
                            **_publication_metadata(document.published),
                            "consultant_type": consultant_type,
                            "query_hash": query_hash,
                            **document.metadata,
                        }
                    )
                )
        if chunk_ids:
            self._upsert_batches(collection, ids=chunk_ids, documents=chunk_texts, metadatas=metadatas)
        return len(chunk_ids)

    def _collection_exists(self, name: str) -> bool:
        try:
            self.client.get_collection(name=name, embedding_function=self.embedding_function)
            return True
        except Exception:
            return False

    def require_general_index(self) -> None:
        if not self._collection_exists(GENERAL_COLLECTION) or not self.general_corpus_path.exists():
            raise FileNotFoundError(
                f"General RAG index is missing under {self.root_dir}. "
                "The offline general index path is deprecated; use ConsultantRAGAgent.ensure_index(...) for runtime retrieval."
            )
        manifest = self.load_manifest()
        expected_backend = str(manifest.get("embedding_backend", "")).strip().lower()
        expected_model = str(manifest.get("embedding_model", "")).strip()
        if expected_backend and expected_backend != self.embedding_backend:
            raise RuntimeError(
                f"General RAG index under {self.root_dir} was built with embedding backend "
                f"'{expected_backend}', but runtime requested '{self.embedding_backend}'."
            )
        if expected_model and expected_model != self.embedding_model:
            raise RuntimeError(
                f"General RAG index under {self.root_dir} was built with embedding model "
                f"'{expected_model}', but runtime requested '{self.embedding_model}'."
            )

    def _build_hits(self, query_result: Dict[str, object]) -> List[RAGHit]:
        hits: List[RAGHit] = []
        documents = query_result.get("documents", [[]])
        metadatas = query_result.get("metadatas", [[]])
        distances = query_result.get("distances", [[]])
        for document_text, metadata, distance in zip(documents[0], metadatas[0], distances[0]):
            if not isinstance(metadata, dict):
                metadata = {}
            score = 1.0 / (1.0 + float(distance if distance is not None else 1.0))
            snippet = re.sub(r"\s+", " ", str(document_text or "")).strip()[:320]
            hits.append(
                RAGHit(
                    doc_id=str(metadata.get("doc_id", "")),
                    title=str(metadata.get("title", "")),
                    source=str(metadata.get("source", "")),
                    score=score,
                    snippet=snippet,
                    url=str(metadata.get("url", "")),
                    doc_type=str(metadata.get("doc_type", "")),
                    source_id=str(metadata.get("source_id", "")),
                    published=str(metadata.get("published", "")),
                    doi=str(metadata.get("doi", "")),
                    is_runtime_fallback=bool(metadata.get("is_runtime_fallback", False)),
                    chunk_id=str(metadata.get("chunk_id", "")),
                    section_type=str(metadata.get("section_type", "")),
                    section_heading=str(metadata.get("section_heading", "")),
                    metadata=dict(metadata),
                )
            )
        return hits

    def search_general(self, query_text: str, n_results: int = 12) -> List[RAGHit]:
        self.require_general_index()
        collection = self._get_or_create_collection(GENERAL_COLLECTION)
        return self._build_hits(collection.query(query_texts=[query_text], n_results=n_results))

    def search_runtime(self, collection_name: str, query_text: str, n_results: int = 12) -> List[RAGHit]:
        if not self._collection_exists(collection_name):
            raise FileNotFoundError(
                f"Runtime RAG index '{collection_name}' is missing under {self.root_dir}. "
                "Call ConsultantRAGAgent.ensure_index(...) before retrieval."
            )
        collection = self._get_or_create_collection(collection_name)
        return self._build_hits(collection.query(query_texts=[query_text], n_results=n_results))

    def search_session(self, query_text: str, n_results: int = 12) -> List[RAGHit]:
        return self.search_runtime(SESSION_GENERAL_COLLECTION, query_text, n_results=n_results)

    def search_core(self, query_text: str, consultant_type: str, query_hash: str, n_results: int = 8) -> List[RAGHit]:
        if not self._collection_exists(CORE_COLLECTION):
            return []
        collection = self._get_or_create_collection(CORE_COLLECTION)
        result = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where={"$and": [{"consultant_type": consultant_type}, {"query_hash": query_hash}]},
        )
        return self._build_hits(result)

    def write_manifest(self, payload: Dict[str, object]) -> None:
        with open(self.manifest_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
