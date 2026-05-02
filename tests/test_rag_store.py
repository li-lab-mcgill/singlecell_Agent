import sys
import tempfile
import types
import unittest
from pathlib import Path


if "chromadb" not in sys.modules:
    fake_chromadb = types.ModuleType("chromadb")
    fake_chromadb.PersistentClient = object
    sys.modules["chromadb"] = fake_chromadb

if "chromadb.utils" not in sys.modules:
    sys.modules["chromadb.utils"] = types.ModuleType("chromadb.utils")

if "chromadb.utils.embedding_functions" not in sys.modules:
    fake_embedding_functions = types.ModuleType("chromadb.utils.embedding_functions")
    fake_embedding_functions.SentenceTransformerEmbeddingFunction = object
    fake_embedding_functions.OpenAIEmbeddingFunction = object
    sys.modules["chromadb.utils.embedding_functions"] = fake_embedding_functions


from rag.store_backend import RAGStore, _publication_metadata
from rag.types import RAGDocument, RAGSection


class RagStoreTests(unittest.TestCase):
    def test_publication_metadata_parses_year_only(self):
        metadata = _publication_metadata("2025")
        self.assertEqual(metadata["publication_year"], 2025)
        self.assertNotIn("publication_month", metadata)

    def test_publication_metadata_parses_pubmed_style_date(self):
        metadata = _publication_metadata("2023 Dec 16")
        self.assertEqual(
            metadata,
            {
                "publication_year": 2023,
                "publication_month": 12,
                "publication_day": 16,
                "publication_date_iso": "2023-12-16",
            },
        )

    def test_publication_metadata_parses_month_without_day(self):
        metadata = _publication_metadata("2020 Mar")
        self.assertEqual(metadata["publication_year"], 2020)
        self.assertEqual(metadata["publication_month"], 3)
        self.assertEqual(metadata["publication_date_iso"], "2020-03")

    def test_chunk_document_preserves_section_boundaries(self):
        store = RAGStore.__new__(RAGStore)
        document = RAGDocument(
            doc_id="pmc:1",
            source="pmc",
            source_id="1",
            title="Example paper",
            text="",
            abstract="",
            doc_type="core_full_text",
            sections=[
                RAGSection(section_id="abstract:0", section_type="abstract", heading="Abstract", text="Short abstract text.", order=0),
                RAGSection(section_id="methods:1", section_type="methods", heading="Methods", text="Methods paragraph one.\n\nMethods paragraph two.", order=1),
            ],
        )
        chunks = store._chunk_document(document)
        self.assertEqual([chunk.section_type for chunk in chunks], ["abstract", "methods"])
        self.assertEqual([chunk.section_heading for chunk in chunks], ["Abstract", "Methods"])
        self.assertTrue(all(chunk.doc_id == "pmc:1" for chunk in chunks))

    def test_reset_runtime_artifacts_clears_sessions_and_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RAGStore.__new__(RAGStore)
            store.sessions_dir = Path(tmpdir) / "sessions"
            store.cache_dir = Path(tmpdir) / "cache"
            store.sessions_dir.mkdir(parents=True, exist_ok=True)
            store.cache_dir.mkdir(parents=True, exist_ok=True)
            (store.sessions_dir / "old.json").write_text("x", encoding="utf-8")
            (store.cache_dir / "old.json").write_text("y", encoding="utf-8")

            store.reset_runtime_artifacts()

            self.assertTrue(store.sessions_dir.exists())
            self.assertTrue(store.cache_dir.exists())
            self.assertEqual(list(store.sessions_dir.iterdir()), [])
            self.assertEqual(list(store.cache_dir.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
