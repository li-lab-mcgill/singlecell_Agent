import sys
import types
import unittest


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


from rag.store_backend import dedup_cross_source
from rag.types import RAGDocument


def _doc(
    *,
    doc_id: str,
    doi: str = "",
    title: str = "",
    source: str = "pubmed",
    doc_type: str = "general",
    text: str = "abstract text",
    full_text_status: str | None = None,
) -> RAGDocument:
    metadata = {}
    if full_text_status is not None:
        metadata["full_text_status"] = full_text_status
    return RAGDocument(
        doc_id=doc_id,
        source=source,
        source_id=doc_id.split(":")[-1],
        title=title,
        text=text,
        doi=doi,
        doc_type=doc_type,
        metadata=metadata,
    )


class CrossSourceDedupTests(unittest.TestCase):
    def test_cross_source_dedup_collapses_same_doi(self):
        docs = [
            _doc(doc_id="pubmed:1", doi="10.1/x", title="A Paper"),
            _doc(doc_id="semantic_scholar:2", doi="10.1/x", title="A Paper"),
            _doc(doc_id="openalex:3", doi="10.1/X", title="a paper"),
        ]

        out = dedup_cross_source(docs)

        self.assertEqual(len(out), 1)

    def test_cross_source_dedup_falls_back_to_normalized_title_when_doi_missing(self):
        docs = [
            _doc(doc_id="pubmed:1", doi="", title="Single-cell atlas of the human cortex"),
            _doc(doc_id="semantic_scholar:2", doi="", title="Single-Cell Atlas Of The Human Cortex!"),
        ]

        out = dedup_cross_source(docs)

        self.assertEqual(len(out), 1)

    def test_cross_source_dedup_keeps_distinct_papers_separate(self):
        docs = [
            _doc(doc_id="pubmed:1", doi="10.1/x", title="Paper X"),
            _doc(doc_id="pubmed:2", doi="10.2/y", title="Paper Y"),
        ]

        out = dedup_cross_source(docs)

        self.assertEqual(len(out), 2)

    def test_cross_source_dedup_prefers_full_text_over_abstract_only(self):
        abstract_only = _doc(
            doc_id="semantic_scholar:2",
            doi="10.1/x",
            title="A Paper",
            source="semantic_scholar",
            doc_type="general",
            full_text_status="abstract_only",
        )
        full_text = _doc(
            doc_id="pmc:1",
            doi="10.1/x",
            title="A Paper",
            source="pmc",
            doc_type="core_full_text",
            full_text_status="pmc_xml",
            text="full body text with methods and results",
        )

        out = dedup_cross_source([abstract_only, full_text])

        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].doc_id, "pmc:1")
        self.assertEqual(out[0].doc_type, "core_full_text")


if __name__ == "__main__":
    unittest.main()
