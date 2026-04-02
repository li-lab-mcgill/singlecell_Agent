from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from rag_types import RAGChunk, RAGDocument, RAGHit

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
DEFAULT_LOCAL_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DEFAULT_OPENAI_EMBEDDING_MODEL = "text-embedding-3-large"


def _normalize_title(text: str) -> str:
    return re.sub(r"\W+", " ", str(text or "").lower()).strip()


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


class RAGStore:
    def __init__(
        self,
        root_dir: str | Path,
        embedding_model: Optional[str] = None,
        embedding_backend: str = "local",
    ):
        if chromadb is None:
            raise RuntimeError("RAG support requires chromadb. Install it before running rag_prepare.py or default.py.")
        self.root_dir = Path(root_dir)
        self.raw_dir = self.root_dir / "raw"
        self.processed_dir = self.root_dir / "processed"
        self.cache_dir = self.root_dir / "cache"
        self.chroma_dir = self.root_dir / "chroma"
        for directory in [self.raw_dir, self.processed_dir, self.cache_dir, self.chroma_dir]:
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

    def core_cache_path(self, cache_key: str) -> Path:
        safe_name = re.sub(r"[^a-zA-Z0-9_.:-]+", "_", cache_key)
        return self.cache_dir / f"{safe_name}.json"

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
        seen_source_ids = set()
        seen_dois = set()
        seen_titles = set()
        for document in documents:
            source_key = (document.source, document.source_id)
            title_key = _normalize_title(document.title)
            doi_key = document.doi.lower().strip()
            if source_key in seen_source_ids:
                continue
            if doi_key and doi_key in seen_dois:
                continue
            if title_key and title_key in seen_titles:
                continue
            seen_source_ids.add(source_key)
            if doi_key:
                seen_dois.add(doi_key)
            if title_key:
                seen_titles.add(title_key)
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
        paragraphs = [part.strip() for part in re.split(r"\n{2,}", text or "") if part.strip()]
        if not paragraphs:
            cleaned = re.sub(r"\s+", " ", text or "").strip()
            return [cleaned] if cleaned else []
        chunks: List[str] = []
        current = ""
        for paragraph in paragraphs:
            candidate = paragraph if not current else f"{current}\n\n{paragraph}"
            if len(candidate) <= chunk_size:
                current = candidate
                continue
            if current:
                chunks.append(current)
                tail = current[-overlap:] if overlap > 0 else ""
                current = f"{tail}\n\n{paragraph}".strip() if tail else paragraph
            else:
                chunks.append(paragraph[:chunk_size])
                current = paragraph[chunk_size - overlap :].strip() if overlap > 0 else ""
        if current:
            chunks.append(current)
        return chunks

    def _chunk_document(self, document: RAGDocument) -> List[RAGChunk]:
        base_text = document.searchable_text()
        chunk_size = 1500 if document.doc_type.startswith("core") else 900
        overlap = 200 if document.doc_type.startswith("core") else 120
        chunks = self._chunk_text(base_text, chunk_size=chunk_size, overlap=overlap)
        return [
            RAGChunk(
                chunk_id=f"{document.doc_id}::chunk::{idx}",
                doc_id=document.doc_id,
                source=document.source,
                title=document.title,
                text=chunk,
                doc_type=document.doc_type,
                metadata=dict(document.metadata),
            )
            for idx, chunk in enumerate(chunks)
        ]

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
                            "published": document.published,
                            "doi": document.doi,
                            **chunk.metadata,
                        }
                    )
                )
        if chunk_ids:
            collection.upsert(ids=chunk_ids, documents=chunk_texts, metadatas=metadatas)
        return len(chunk_ids)

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
                            "published": document.published,
                            "doi": document.doi,
                            "consultant_type": consultant_type,
                            "query_hash": query_hash,
                            **document.metadata,
                        }
                    )
                )
        if chunk_ids:
            collection.upsert(ids=chunk_ids, documents=chunk_texts, metadatas=metadatas)
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
                "Run rag_prepare.py before default.py."
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
                    metadata=dict(metadata),
                )
            )
        return hits

    def search_general(self, query_text: str, n_results: int = 12) -> List[RAGHit]:
        self.require_general_index()
        collection = self._get_or_create_collection(GENERAL_COLLECTION)
        return self._build_hits(collection.query(query_texts=[query_text], n_results=n_results))

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
