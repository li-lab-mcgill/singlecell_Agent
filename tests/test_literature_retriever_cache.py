"""Tests for the HyDE-abstract cache in LiteratureRetriever.

The three scientist panelists (biologist, statistician, bioinformatician)
share one LiteratureRetriever instance (see ScientistPanel.__init__ and
agents/panelist_tools.py::build_panelist_tool_registry) and run concurrently
in a ThreadPoolExecutor (agents/scientist_panel.py::_run_parallel). They often
issue overlapping subqueries (the same base_query text), which previously
caused LiteratureRetriever._generate_subqueries (the HyDE-abstract LLM call)
to be redundantly re-run for identical retrieval requests.

Design under test: ONLY the HyDE abstract/subquery generation result is
cached, keyed on the normalized base_query. `_generate_subqueries` is a pure
function of query text -- it does not depend on the document index, `role`,
or which research phase/question is in flight -- so reusing it is always
safe, with no staleness risk and no need for phase-boundary cache resets.

Search (`_rrf_search` / `store.search_runtime`) is deliberately NEVER cached:
each `retrieve()` call must fetch+search fresh against the current index, so
a cache hit never discards freshly fetched documents in favor of stale
results from a different phase/question -- the exact staleness bug this
design avoids.

These tests verify:
1. Issuing the same normalized subquery twice triggers HyDE generation only
   once (second call is a cache hit), while search_runtime is invoked on
   BOTH calls (search is never cached -- no staleness possible).
2. reset_cache() clears the HyDE cache (available for tests / eager memory
   bounding), even though it is not required for correctness.
"""

from __future__ import annotations

import sys
import types
import unittest

# rag/store_backend.py imports chromadb at module load time; stub it out so
# this test doesn't require the real dependency (same pattern used in
# tests/test_retrieval_dedup.py).
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

from rag.literature_retriever import LiteratureRetriever
from rag.types import RAGDocument, RAGHit


def _doc(doc_id: str) -> RAGDocument:
    return RAGDocument(
        doc_id=doc_id,
        source="pubmed",
        source_id=doc_id.split(":")[-1],
        title=f"Paper {doc_id}",
        text="abstract text",
        abstract="abstract text",
        doi=f"10.1/{doc_id}",
    )


class _FakeStore:
    """Stand-in for RAGStore: no chromadb, just enough surface for retrieve()."""

    def __init__(self, tmp_path):
        self.root_dir = tmp_path
        self.build_calls = 0
        self.search_calls = 0

    def build_runtime_index(self, collection_name, documents, rebuild=True):
        self.build_calls += 1

    def search_runtime(self, collection_name, query_text, n_results=12):
        self.search_calls += 1
        return [
            RAGHit(
                doc_id="pubmed:1",
                title="Paper pubmed:1",
                source="pubmed",
                score=0.9,
                snippet="",
                url="",
                doc_type="general",
                source_id="1",
            )
        ]


class _FakeClient:
    """Never actually called in these tests -- retrieve()'s internal LLM
    steps (_generate_queries, _generate_subqueries) are monkeypatched directly
    so no real HTTP call is made."""

    pass


def _make_retriever(tmp_path) -> tuple[LiteratureRetriever, _FakeStore]:
    store = _FakeStore(tmp_path)
    retriever = LiteratureRetriever(
        rag_store=store,
        engine_name="fake-engine",
        client=_FakeClient(),
        cache_dir=tmp_path / "lit_cache",
    )
    # Stub steps 1-2 (keyword query generation + multi-source fetch): these
    # are unrelated to the HyDE cache under test here, so replace them with
    # cheap fakes that avoid real LLM/network calls.
    retriever._generate_queries = lambda **kwargs: {  # type: ignore[method-assign]
        "pubmed_queries": ["q"],
        "natural_queries": ["q"],
    }
    retriever._fetch_documents = lambda **kwargs: [_doc("pubmed:1")]  # type: ignore[method-assign]
    return retriever, store


def _wrap_with_counter(fn):
    """Wrap a bound method with a call counter, returning (counter, wrapped)."""
    counter = {"n": 0}

    def wrapped(**kwargs):
        counter["n"] += 1
        return fn(**kwargs)

    return counter, wrapped


class LiteratureRetrieverCacheTests(unittest.TestCase):
    def test_repeated_subquery_caches_hyde_but_always_searches_fresh(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            retriever, store = _make_retriever(Path(tmp))
            hyde_calls, counting_generate_subqueries = _wrap_with_counter(retriever._generate_subqueries)
            retriever._generate_subqueries = counting_generate_subqueries  # type: ignore[method-assign]

            # First call: cache miss -- HyDE generation runs, search runs.
            retriever.retrieve(
                base_query="  T cell exhaustion markers IBD  ",
                background="8k PBMC cells, IBD vs healthy",
                role="biologist",
            )
            self.assertEqual(hyde_calls["n"], 1)
            self.assertEqual(store.search_calls, 1)

            # Second call: same subquery after normalization (different case/
            # whitespace, different role -- as if a different panelist issued
            # it). HyDE generation must be a cache hit (query-text-deterministic,
            # always safe to reuse). Search must NOT be cached -- it must run
            # again against the freshly fetched documents, so a different
            # phase/question can never receive another phase's stale results.
            retriever.retrieve(
                base_query="t cell exhaustion markers ibd",
                background="8k PBMC cells, IBD vs healthy",
                role="statistician",
            )
            self.assertEqual(
                hyde_calls["n"], 1,
                "HyDE generator must not be invoked again for a repeated normalized subquery",
            )
            self.assertEqual(
                store.search_calls, 2,
                "search_runtime must run fresh on every retrieve() call -- it is never cached",
            )

    def test_reset_cache_clears_hyde_cache(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            retriever, store = _make_retriever(Path(tmp))
            hyde_calls, counting_generate_subqueries = _wrap_with_counter(retriever._generate_subqueries)
            retriever._generate_subqueries = counting_generate_subqueries  # type: ignore[method-assign]

            retriever.retrieve(
                base_query="T cell exhaustion markers IBD",
                background="8k PBMC cells, IBD vs healthy",
                role="biologist",
            )
            self.assertEqual(hyde_calls["n"], 1)

            # Cache hit without a reset: still just 1 HyDE call.
            retriever.retrieve(
                base_query="T cell exhaustion markers IBD",
                background="8k PBMC cells, IBD vs healthy",
                role="biologist",
            )
            self.assertEqual(hyde_calls["n"], 1)

            # reset_cache() is not required for correctness (HyDE generation
            # is a pure function of query text, so there is no staleness to
            # guard against) but remains available, e.g. for eager memory
            # bounding -- verify it actually clears the cache.
            retriever.reset_cache()

            retriever.retrieve(
                base_query="T cell exhaustion markers IBD",
                background="8k PBMC cells, IBD vs healthy",
                role="biologist",
            )
            self.assertEqual(
                hyde_calls["n"], 2,
                "reset_cache() must clear the HyDE cache so the next call regenerates",
            )


if __name__ == "__main__":
    unittest.main()
