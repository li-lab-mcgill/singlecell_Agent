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
from rag.literature_retriever import rrf_fuse, DEFAULT_RRF_K
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


class RRFPerDocumentAggregationTests(unittest.TestCase):
    def test_rrf_aggregates_chunks_per_document(self):
        # doc "full" has chunks at ranks 1,2,3; doc "abs" one chunk at rank 4.
        # A multi-chunk document must not accumulate one RRF increment per
        # chunk occurrence -- only its single best (first/lowest) rank counts.
        ranked = [[("full", 0.9), ("full", 0.8), ("full", 0.7), ("abs", 0.6)]]

        scores = rrf_fuse(ranked)

        # "full" must not get 3x the increments of "abs"
        self.assertLessEqual(scores["full"], 1.0 / (DEFAULT_RRF_K + 1) + 1e-9)
        self.assertAlmostEqual(scores["full"], 1.0 / (DEFAULT_RRF_K + 1))
        self.assertAlmostEqual(scores["abs"], 1.0 / (DEFAULT_RRF_K + 2))

    def test_rrf_fuse_sums_across_multiple_ranked_lists(self):
        ranked_lists = [
            [("a", 0.9), ("b", 0.8)],
            [("b", 0.95), ("a", 0.7)],
        ]

        scores = rrf_fuse(ranked_lists, k=1)

        self.assertAlmostEqual(scores["a"], 1.0 / 2 + 1.0 / 3)
        self.assertAlmostEqual(scores["b"], 1.0 / 3 + 1.0 / 2)

    def test_rrf_fuse_ignores_repeat_doc_id_appearing_later_in_same_list(self):
        # Even a non-consecutive repeat of a doc_id within one ranked list
        # must not contribute a second increment.
        ranked_lists = [[("x", 0.9), ("y", 0.8), ("x", 0.5)]]

        scores = rrf_fuse(ranked_lists, k=1)

        self.assertAlmostEqual(scores["x"], 1.0 / 2)
        self.assertAlmostEqual(scores["y"], 1.0 / 3)


if __name__ == "__main__":
    unittest.main()
