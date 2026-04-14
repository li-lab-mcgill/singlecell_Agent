import sys
import types
import unittest
from unittest.mock import patch


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

if "textgrad" not in sys.modules:
    fake_textgrad = types.ModuleType("textgrad")
    fake_textgrad.get_engine = lambda *args, **kwargs: None
    sys.modules["textgrad"] = fake_textgrad

if "requests" not in sys.modules:
    fake_requests = types.ModuleType("requests")

    class _FakeResponse:
        def __init__(self):
            self.status_code = 200

    class _FakeHTTPError(Exception):
        def __init__(self, message="", response=None):
            super().__init__(message)
            self.response = response

    fake_requests.ConnectionError = type("ConnectionError", (Exception,), {})
    fake_requests.Timeout = type("Timeout", (Exception,), {})
    fake_requests.Response = _FakeResponse
    fake_requests.HTTPError = _FakeHTTPError
    fake_requests.Session = type("Session", (), {})
    sys.modules["requests"] = fake_requests

if "config" not in sys.modules:
    fake_config = types.ModuleType("config")
    fake_config.Config = object
    sys.modules["config"] = fake_config


from rag_agent import BASE_QUERIES, ConsultantRAGAgent
from rag_types import PromotedPaper, RAGDocument, RAGSection


class _FakeStore:
    @staticmethod
    def _chunk_text(text, chunk_size, overlap):
        if len(text) <= chunk_size:
            return [text]
        chunks = []
        start = 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            chunks.append(text[start:end])
            if end == len(text):
                break
            start = max(0, end - overlap)
        return chunks


class RagAgentTests(unittest.TestCase):
    def test_validate_keyword_payload_returns_only_pubmed_queries(self):
        agent = ConsultantRAGAgent.__new__(ConsultantRAGAgent)
        queries = agent._validate_keyword_payload(
            {
                "pubmed_queries": [
                    '"PBMC" AND "scRNA-seq"',
                    '("PBMC" OR "peripheral blood mononuclear cells") AND scRNA-seq AND pmc[Filter]',
                ]
            }
        )
        self.assertEqual(
            queries,
            [
                '"PBMC" AND "scRNA-seq"',
                '("PBMC" OR "peripheral blood mononuclear cells") AND scRNA-seq',
            ],
        )

    def test_validate_subquery_payload_requires_subquery_and_hyde_abstract(self):
        agent = ConsultantRAGAgent.__new__(ConsultantRAGAgent)
        items = agent._validate_subquery_payload(
            {
                "items": [
                    {"subquery": "PBMC markers", "hyde_abstract": "Scientific abstract."},
                    {"subquery": "missing abstract"},
                    {"hyde_abstract": "missing subquery"},
                ]
            }
        )
        self.assertEqual(items, [{"subquery": "PBMC markers", "hyde_abstract": "Scientific abstract."}])

    def test_validate_channel_plan_requires_pubmed_queries_and_items(self):
        agent = ConsultantRAGAgent.__new__(ConsultantRAGAgent)
        payload = agent._validate_channel_plan(
            {
                "pubmed_queries": ['"PBMC" AND "scRNA-seq"'],
                "items": [{"subquery": "PBMC markers", "hyde_abstract": "Scientific abstract."}],
            }
        )
        self.assertEqual(payload["pubmed_queries"], ['"PBMC" AND "scRNA-seq"'])
        self.assertEqual(payload["items"][0]["subquery"], "PBMC markers")

    def test_sanitize_pubmed_query_strips_pmc_filter(self):
        agent = ConsultantRAGAgent.__new__(ConsultantRAGAgent)
        cleaned = agent._sanitize_pubmed_query(
            '("PBMC" OR "peripheral blood mononuclear cells") AND scRNA-seq AND pmc[Filter]'
        )
        self.assertNotIn("pmc[Filter]", cleaned)
        self.assertEqual(
            cleaned,
            '("PBMC" OR "peripheral blood mononuclear cells") AND scRNA-seq'
        )

    def test_sanitize_pubmed_query_removes_unbalanced_parentheses(self):
        agent = ConsultantRAGAgent.__new__(ConsultantRAGAgent)
        cleaned = agent._sanitize_pubmed_query(
            '("single-cell Multiome" OR "10x Multiome") AND PBMC) AND "RNA-seq"'
        )
        self.assertEqual(
            cleaned,
            '("single-cell Multiome" OR "10x Multiome") AND PBMC AND "RNA-seq"'
        )

    def test_rrf_fuse_boosts_papers_retrieved_across_multiple_subqueries(self):
        agent = ConsultantRAGAgent.__new__(ConsultantRAGAgent)
        documents_by_id = {
            "pmc:1": RAGDocument(doc_id="pmc:1", source="pmc", source_id="1", title="Shared paper", text="x"),
            "pmc:2": RAGDocument(doc_id="pmc:2", source="pmc", source_id="2", title="Unique paper", text="x"),
        }
        ranked_lists = [
            [{"paper_id": "pmc:1", "best_section_type": "methods", "best_snippet": "shared", "score": 0.9}],
            [
                {"paper_id": "pmc:2", "best_section_type": "results", "best_snippet": "unique", "score": 0.95},
                {"paper_id": "pmc:1", "best_section_type": "discussion", "best_snippet": "shared again", "score": 0.8},
            ],
        ]
        fused = agent._rrf_fuse(ranked_lists, documents_by_id, k=1)
        self.assertIsInstance(fused[0], PromotedPaper)
        self.assertEqual(fused[0].doc_id, "pmc:1")

    def test_fetch_paper_section_returns_section_chunks_for_long_text(self):
        agent = ConsultantRAGAgent.__new__(ConsultantRAGAgent)
        agent.store = _FakeStore()
        long_text = "A" * 4500
        agent._paper_documents_by_id = {
            "pmc:1": RAGDocument(
                doc_id="pmc:1",
                source="pmc",
                source_id="1",
                title="Example paper",
                text="",
                sections=[
                    RAGSection(section_id="methods:0", section_type="methods", heading="Methods", text=long_text, order=0)
                ],
            )
        }
        payload = agent.fetch_paper_section("pmc:1", "Methods")
        self.assertEqual(payload["section_type"], "methods")
        self.assertIn("chunks", payload)
        self.assertGreater(len(payload["chunks"]), 1)

    def test_resolve_base_query_keeps_existing_dataset_query_unchanged(self):
        agent = ConsultantRAGAgent.__new__(ConsultantRAGAgent)
        config = types.SimpleNamespace(feat_stats="PBMC dataset", task_type="Integration", learning_type="Unsupervised")
        self.assertEqual(
            agent._resolve_base_query("dataset", config, "background"),
            BASE_QUERIES["dataset"],
        )

    def test_task_descriptor_uses_real_task_block_from_background(self):
        agent = ConsultantRAGAgent.__new__(ConsultantRAGAgent)
        config = types.SimpleNamespace(learning_type="Unsupervised")
        background = """
        DATA:
        Something.

        TASK:
        Develop a prior guided unsupervised deep learning Python pipeline for single-cell RNA-seq representation learning.

        The pipeline MUST:
        1. Use fixed scripts.
        """
        self.assertEqual(
            agent._task_descriptor(config, background),
            "Develop a prior guided unsupervised deep learning Python pipeline for single-cell RNA-seq representation learning.",
        )

    def test_build_keyword_background_is_channel_specific(self):
        agent = ConsultantRAGAgent.__new__(ConsultantRAGAgent)
        agent._dataset_descriptor = lambda config, background="": "human PBMC 10x scRNA-seq"
        agent._prior_resource_names = lambda config: ["CellMarker.csv", "GO_terms.csv"]
        agent._prior_resource_types = lambda config: ["marker_genes", "gene_ontology"]
        agent._task_descriptor = lambda config, background="": "unsupervised representation learning and clustering"
        config = types.SimpleNamespace()

        dataset_background = agent._build_keyword_background(
            channel_name="dataset",
            config=config,
            background="dataset background",
        )
        self.assertIn("DATASET DESCRIPTION:", dataset_background)
        self.assertIn("human PBMC 10x scRNA-seq", dataset_background)
        self.assertNotIn("RESEARCH BACKGROUND:", dataset_background)

        resource_background = agent._build_keyword_background(
            channel_name="prior_resources",
            config=config,
            background="resource background",
        )
        self.assertIn("AVAILABLE PRIOR RESOURCES:", resource_background)
        self.assertIn("CellMarker.csv, GO_terms.csv", resource_background)
        self.assertNotIn("RESEARCH BACKGROUND:", resource_background)

        method_background = agent._build_keyword_background(
            channel_name="prior_methods",
            config=config,
            background="method background",
        )
        self.assertIn("AVAILABLE PRIOR RESOURCE TYPES:", method_background)
        self.assertIn("marker_genes, gene_ontology", method_background)
        self.assertIn("TASK:", method_background)
        self.assertNotIn("RESEARCH BACKGROUND:", method_background)

        benchmark_background = agent._build_keyword_background(
            channel_name="benchmark",
            config=config,
            background="benchmark background",
        )
        self.assertIn("DATASET CONTEXT:", benchmark_background)
        self.assertIn("TASK:", benchmark_background)
        self.assertNotIn("RESEARCH BACKGROUND:", benchmark_background)

    def test_generate_channel_plan_combines_keyword_and_subquery_generation(self):
        agent = ConsultantRAGAgent.__new__(ConsultantRAGAgent)
        agent._generate_pubmed_queries = lambda **kwargs: ['"PBMC" AND "scRNA-seq"']
        agent._generate_subquery_items = lambda **kwargs: [
            {"subquery": "PBMC markers", "hyde_abstract": "Scientific abstract."}
        ]
        plan = agent._generate_channel_plan(
            channel_name="dataset",
            config=types.SimpleNamespace(),
            background="PBMC background",
            base_query=BASE_QUERIES["dataset"],
        )
        self.assertEqual(plan["pubmed_queries"], ['"PBMC" AND "scRNA-seq"'])
        self.assertEqual(plan["items"], [{"subquery": "PBMC markers", "hyde_abstract": "Scientific abstract."}])

    def test_generate_channel_plan_requests_ten_pubmed_queries(self):
        agent = ConsultantRAGAgent.__new__(ConsultantRAGAgent)
        captured = {}

        def _fake_generate_pubmed_queries(**kwargs):
            captured.update(kwargs)
            return ['"PBMC" AND "scRNA-seq"']

        agent._generate_pubmed_queries = _fake_generate_pubmed_queries
        agent._generate_subquery_items = lambda **kwargs: [
            {"subquery": "PBMC markers", "hyde_abstract": "Scientific abstract."}
        ]
        agent._generate_channel_plan(
            channel_name="dataset",
            config=types.SimpleNamespace(),
            background="PBMC background",
            base_query=BASE_QUERIES["dataset"],
        )
        self.assertEqual(captured["n_queries"], 10)

    def test_generate_channel_plan_requests_twenty_pubmed_queries_for_prior_methods(self):
        agent = ConsultantRAGAgent.__new__(ConsultantRAGAgent)
        captured = {}

        def _fake_generate_pubmed_queries(**kwargs):
            captured.update(kwargs)
            return ['"PBMC" AND "scRNA-seq"']

        agent._generate_pubmed_queries = _fake_generate_pubmed_queries
        agent._generate_subquery_items = lambda **kwargs: [
            {"subquery": "prior-guided methods", "hyde_abstract": "Scientific abstract."}
        ]
        agent._generate_channel_plan(
            channel_name="prior_methods",
            config=types.SimpleNamespace(),
            background="PBMC background",
            base_query=BASE_QUERIES["prior_methods"],
        )
        self.assertEqual(captured["n_queries"], 20)

    def test_prepared_context_cache_is_reused(self):
        agent = ConsultantRAGAgent.__new__(ConsultantRAGAgent)
        agent._prepared_channel_contexts = {
            "__prepared_contexts__": {
                "dataset": {"context": "RAG_DATASET_CONTEXT\ncached", "hits": []},
                "prior_resources": {"context": "RAG_PRIOR_RESOURCE_CONTEXT\ncached", "hits": []},
                "prior_methods": {"context": "RAG_PRIOR_METHOD_CONTEXT\ncached", "hits": []},
                "benchmark": {"context": "RAG_BENCHMARK_CONTEXT\ncached", "hits": []},
            }
        }
        self.assertEqual(
            agent.build_analyst_context(config=None, background="ignored"),
            "RAG_DATASET_CONTEXT\ncached",
        )
        self.assertEqual(
            agent.build_benchmark_context(config=None, background="ignored"),
            "RAG_BENCHMARK_CONTEXT\ncached",
        )

    @patch("rag_agent.fetch_core_document")
    def test_resolve_pmc_document_skips_fetch_errors(self, mock_fetch_core_document):
        agent = ConsultantRAGAgent.__new__(ConsultantRAGAgent)
        agent.store = types.SimpleNamespace(load_cached_core_document=lambda *_: None, save_cached_core_document=lambda *_: None)
        mock_fetch_core_document.side_effect = RuntimeError("PMC efetch failed")
        base_document = RAGDocument(doc_id="pubmed:1", source="pubmed", source_id="1", title="Bad PMC paper", text="x")
        self.assertIsNone(agent._resolve_pmc_document(base_document))


if __name__ == "__main__":
    unittest.main()
