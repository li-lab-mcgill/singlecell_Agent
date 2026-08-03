from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from agents.panelist_tools import (
    FetchPaperContentTool,
    FetchPaperWikiTool,
    RetrieveLiteratureTool,
    SearchPaperWikiTool,
    build_panelist_tool_registry,
    build_paper_detail_tool_registry,
    _deduplicate_papers,
)
from agents.scientist_panel import ScientistPanel


class _FakeRetriever:
    def __init__(self, papers=None):
        self.papers = list(papers or [])
        self.calls = []

    def retrieve(self, **kwargs):
        self.calls.append(kwargs)
        return list(self.papers)

    def fetch_paper_section(self, paper_id, section_type):
        if paper_id == "pmc:1":
            return {
                "paper_id": paper_id,
                "title": "Fresh paper",
                "section_type": section_type,
                "section_heading": section_type.title(),
                "text": "Fresh content.",
            }
        return {"error": "not found"}


class _FakeJudge:
    def __init__(self):
        self.calls = []

    def judge(self, *, papers, role, retrieval_intent, retrieval_goal, base_query, threshold):
        self.calls.append(
            {
                "papers": papers,
                "role": role,
                "retrieval_intent": retrieval_intent,
                "retrieval_goal": retrieval_goal,
                "base_query": base_query,
                "threshold": threshold,
            }
        )
        return [
            {
                **paper,
                "relevant": paper.get("relevant", True),
                "confidence": paper.get("confidence", 0.80),
                "reason": "Useful for this retrieval intent.",
                "evidence_contribution": "Contributes an evidence pattern.",
            }
            for paper in papers
        ]


class _FakeWriter:
    def __init__(self):
        self.batches = []

    def write_batch(self, papers):
        self.batches.append(list(papers))
        return [str(p.get("paper_id") or p.get("doc_id")) for p in papers]


class _FailingWriter:
    def write_batch(self, papers):
        raise RuntimeError("wiki write failed")


class _FakePaperIndex:
    def __init__(self):
        self.calls = []

    def query_papers(self, **kwargs):
        self.calls.append(kwargs)
        return [
            {
                "paper_id": "wiki_1",
                "title": "Wiki paper",
                "doi": "10.1/wiki",
                "url": "https://example.org/wiki",
                "full_text_status": "pmc_xml",
                "retrieval_goals": [kwargs["retrieval_goal"]],
                "retrieval_intents": [kwargs["retrieval_intent"]],
                "tasks": ["rna_differential_abundance"],
                "extends": [],
                "content": """## Summary
Wiki summary.

## Background
Wiki background.

## Key findings
Wiki finding.

## Analysis
Wiki analysis.

## Benchmark methods
Wiki benchmark.

## Limitations
Wiki limitation.

## Metrics used
Wiki metric.

## Figure captions
Figure 1: Wiki caption.
""",
            }
        ]

    def get_paper(self, paper_id):
        if paper_id != "wiki_1":
            return None
        return self.query_papers(
            retrieval_goal="evidence_pattern",
            retrieval_intent="intent",
        )[0]


class PanelistLiteratureToolTests(unittest.TestCase):
    def test_panelist_registry_exposes_three_literature_tools(self):
        registry = build_panelist_tool_registry(
            role="biologist",
            retriever=_FakeRetriever(),
            judge=_FakeJudge(),
            paper_md_writer=None,
        )

        self.assertEqual(
            set(registry.tools),
            {"search_paper_wiki", "retrieve_literature", "fetch_paper_wiki", "fetch_paper_content"},
        )
        self.assertNotIn("query_paper_wiki", registry.tools)
        self.assertNotIn("traverse_paper_wiki", registry.tools)
        self.assertNotIn("get_related_papers", registry.tools)

    def test_search_paper_wiki_returns_canonical_summaries(self):
        tool = SearchPaperWikiTool(role="statistician")
        fake_index = _FakePaperIndex()
        with patch("agents.panelist_tools.get_paper_index", return_value=fake_index):
            result = tool.run(
                retrieval_intent="What statistical unit supports T cell expansion?",
                retrieval_goal="evidence_pattern",
                requirements="Use donor-level inference.",
                background="PBMC disease vs healthy.",
            )

        self.assertTrue(result["sufficient_memory"])
        paper = result["papers"][0]
        self.assertEqual(paper["paper_id"], "wiki_1")
        self.assertEqual(paper["background"], "Wiki background.")
        self.assertEqual(paper["analysis"], "Wiki analysis.")
        self.assertEqual(paper["benchmark_methods"], "Wiki benchmark.")
        self.assertEqual(paper["metrics_used"], "Wiki metric.")
        self.assertEqual(paper["figure_captions"], "Figure 1: Wiki caption.")
        self.assertEqual(paper["paper_sections"]["benchmark_methods"], "Wiki benchmark.")
        self.assertTrue(paper["return_to_panelist"])
        self.assertEqual(paper["source"], "paper_wiki")

    def test_fetch_paper_wiki_returns_curated_summary(self):
        tool = FetchPaperWikiTool()
        fake_index = _FakePaperIndex()
        with patch("agents.panelist_tools.get_paper_index", return_value=fake_index):
            result = tool.run(paper_id="wiki_1")

        self.assertEqual(result["content_status"], "found")
        self.assertEqual(result["summary"], "Wiki summary.")
        self.assertEqual(result["background"], "Wiki background.")
        self.assertEqual(result["analysis"], "Wiki analysis.")
        self.assertEqual(result["benchmark_methods"], "Wiki benchmark.")
        self.assertEqual(result["metrics_used"], "Wiki metric.")
        self.assertEqual(result["figure_captions"], "Figure 1: Wiki caption.")
        self.assertEqual(result["paper_sections"]["analysis"], "Wiki analysis.")

    def test_fetch_paper_content_requires_section_or_query_and_can_read_wiki_section(self):
        tool = FetchPaperContentTool(retriever=_FakeRetriever())
        missing = tool.run(paper_id="wiki_1")
        self.assertIn("requires at least one", missing["error"])

        fake_index = _FakePaperIndex()
        with patch("agents.panelist_tools.get_paper_index", return_value=fake_index):
            result = tool.run(paper_id="wiki_1", section="analysis", max_chars=1000)

        self.assertEqual(result["source"], "paper_wiki")
        self.assertEqual(result["content"], "Wiki analysis.")

    def test_paper_detail_registry_exposes_only_detail_tools(self):
        registry = build_paper_detail_tool_registry(retriever=_FakeRetriever())
        self.assertEqual(set(registry.tools), {"fetch_paper_wiki", "fetch_paper_content"})

    def test_search_paper_wiki_caps_top_k_at_ten(self):
        tool = SearchPaperWikiTool(role="statistician")
        fake_index = _FakePaperIndex()
        with patch("agents.panelist_tools.get_paper_index", return_value=fake_index):
            tool.run(
                retrieval_intent="intent",
                retrieval_goal="evidence_pattern",
                requirements="requirements",
                background="background",
                top_k=50,
            )

        self.assertEqual(fake_index.calls[0]["top_k"], 10)

    def test_retrieve_literature_returns_useful_threshold_and_persists_stricter_threshold(self):
        retriever = _FakeRetriever(
            [
                {
                    "doc_id": "pmc:1",
                    "title": "Moderately useful",
                    "doi": "10.1/moderate",
                    "full_text_status": "pmc_xml",
                    "analysis": "Donor-level model.",
                    "confidence": 0.65,
                },
                {
                    "doc_id": "pmc:2",
                    "title": "Highly useful",
                    "doi": "10.1/high",
                    "full_text_status": "pmc_xml",
                    "analysis": "Mixed model.",
                    "confidence": 0.86,
                },
            ]
        )
        judge = _FakeJudge()
        writer = _FakeWriter()
        tool = RetrieveLiteratureTool(
            retriever=retriever,
            judge=judge,
            role="statistician",
            paper_md_writer=writer,
        )

        result = tool.run(
            retrieval_context_id="ctx1",
            retrieval_intent="Which model supports differential abundance?",
            retrieval_goal="evidence_pattern",
            requirements="Need sample-level inference.",
            background="PBMC disease vs healthy.",
            top_k=8,
        )

        self.assertEqual(judge.calls[0]["threshold"], 0.60)
        self.assertEqual([p["doc_id"] for p in result["papers"]], ["pmc:1", "pmc:2"])
        self.assertTrue(result["papers"][0]["return_to_panelist"])
        self.assertFalse(result["papers"][0]["persist_to_wiki"])
        self.assertTrue(result["papers"][1]["persist_to_wiki"])
        self.assertEqual(len(writer.batches), 1)
        self.assertEqual([p["doc_id"] for p in writer.batches[0]], ["pmc:2"])

    def test_retrieve_literature_returns_papers_when_wiki_persistence_fails(self):
        retriever = _FakeRetriever(
            [
                {
                    "doc_id": "pmc:1",
                    "title": "Highly useful",
                    "doi": "10.1/high",
                    "full_text_status": "pmc_xml",
                    "analysis": "Mixed model.",
                    "confidence": 0.86,
                },
            ]
        )
        tool = RetrieveLiteratureTool(
            retriever=retriever,
            judge=_FakeJudge(),
            role="statistician",
            paper_md_writer=_FailingWriter(),
        )

        result = tool.run(
            retrieval_context_id="ctx1",
            retrieval_intent="Which model supports differential abundance?",
            retrieval_goal="evidence_pattern",
            requirements="Need sample-level inference.",
            background="PBMC disease vs healthy.",
            top_k=8,
        )

        self.assertEqual([p["doc_id"] for p in result["papers"]], ["pmc:1"])
        self.assertIn("wiki write failed", result["persistence_error"])

    def test_abstract_only_papers_are_capped_before_persistence(self):
        retriever = _FakeRetriever(
            [
                {
                    "doc_id": "s2:1",
                    "title": "Abstract only useful paper",
                    "doi": "10.1/abstract",
                    "full_text_status": "abstract_only",
                    "analysis": "Abstract mentions an analysis.",
                    "confidence": 0.95,
                },
            ]
        )
        judge = _FakeJudge()
        writer = _FakeWriter()
        tool = RetrieveLiteratureTool(
            retriever=retriever,
            judge=judge,
            role="biologist",
            paper_md_writer=writer,
        )

        result = tool.run(
            retrieval_context_id="ctx_abs",
            retrieval_intent="intent",
            retrieval_goal="evidence_pattern",
            requirements="requirements",
            background="background",
        )

        self.assertEqual(result["papers"][0]["confidence"], 0.70)
        self.assertTrue(result["papers"][0]["return_to_panelist"])
        self.assertFalse(result["papers"][0]["persist_to_wiki"])
        self.assertEqual(writer.batches, [])

    def test_retrieve_literature_tracks_context_seen_ids_and_accepts_exclude_ids(self):
        retriever = _FakeRetriever(
            [
                {"doc_id": "pmc:1", "title": "A", "doi": "10.1/a", "analysis": "A", "confidence": 0.9},
                {"doc_id": "pmc:2", "title": "B", "doi": "10.1/b", "analysis": "B", "confidence": 0.9},
            ]
        )
        judge = _FakeJudge()
        tool = RetrieveLiteratureTool(
            retriever=retriever,
            judge=judge,
            role="biologist",
            paper_md_writer=None,
        )

        first = tool.run(
            retrieval_context_id="ctx1",
            retrieval_intent="intent",
            retrieval_goal="prior_findings",
            requirements="requirements",
            background="background",
            exclude_ids={"dois": ["10.1/b"]},
        )
        second = tool.run(
            retrieval_context_id="ctx1",
            retrieval_intent="intent",
            retrieval_goal="prior_findings",
            requirements="requirements",
            background="background",
        )

        self.assertEqual([p["doc_id"] for p in first["papers"]], ["pmc:1"])
        self.assertEqual(second["papers"], [])
        self.assertEqual(len(judge.calls), 1)

    def test_deduplicate_papers_collapses_preprint_and_published_title_match(self):
        papers = _deduplicate_papers(
            [
                {
                    "doc_id": "pmc:9915567",
                    "title": "Benchmarking algorithms for joint integration of unpaired and paired single-cell RNA-seq and ATAC-seq data.",
                    "doi": "10.1101/2023.02.01.526609",
                    "full_text_status": "pmc_xml",
                    "confidence": 0.90,
                    "retrieval_intent": "method evidence",
                },
                {
                    "doc_id": "pmc:10594700",
                    "title": "Benchmarking algorithms for joint integration of unpaired and paired single-cell RNA-seq and ATAC-seq data.",
                    "doi": "10.1186/s13059-023-03073-x",
                    "full_text_status": "pmc_xml",
                    "confidence": 0.78,
                    "retrieval_intent": "statistical evidence",
                },
            ],
            use_title_fallback=True,
        )

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0]["doc_id"], "pmc:9915567")


class _FakeCallbackRunner:
    """Stand-in for ToolCallingAgentRunner that records nothing itself; the
    surrounding panel subclass records that it was constructed/invoked."""

    def __init__(self, text: str):
        self._text = text

    def run(self, *, initial_user_input, response_handler=None):
        if response_handler is not None:
            response_handler(self._text)
        return self._text


class _RoutingProbePanel(ScientistPanel):
    """Lightweight ScientistPanel stand-in for exercising callback-type
    dispatch in _run_panelist_callback without any real LLM/tool I/O.

    Mirrors the bypass-heavy-__init__ pattern used in
    tests/test_scientist_panel_callbacks.py's _CallbackPanel.
    """

    def __init__(self):
        self.engine_name = "test-engine"
        self.client = object()
        self.retriever = object()
        self.judge = object()
        self.paper_md_writer = None
        self.short_term_memory = None
        self.result_dir = Path(".")
        self.runner_calls: list[dict] = []

    def _make_runner(self, role, registry, tag="ROUND1"):
        self.runner_calls.append({"role": role, "registry": registry, "tag": tag})
        return _FakeCallbackRunner('<CALLBACK>{"gap_resolved": true}</CALLBACK>')

    def _log_retrieval_evidence(self, **kwargs):
        pass


class RunPanelistCallbackLiteratureRoutingTests(unittest.TestCase):
    """Task 2.1: MediatorAgent emits callback_type="literature"/"reasoning",
    but _run_panelist_callback's retrieval-tool branch only matched the exact
    string "ask_panelist_for_more_literature". run_panelist_callback (the
    entry point wired as MediatorAgent's panelist_callback_executor) must
    normalize the incoming callback_type the same way _extract_callback_requests
    does, so mediator-driven literature callbacks actually retrieve.
    """

    def test_literature_alias_takes_retrieval_tool_branch(self):
        panel = _RoutingProbePanel()

        with patch(
            "agents.scientist_panel.build_panelist_tool_registry",
            return_value="FAKE_REGISTRY",
        ) as mock_build_registry, patch(
            "agents.scientist_panel.single_llm_call",
            return_value='<CALLBACK>{"gap_resolved": true}</CALLBACK>',
        ) as mock_single_llm_call:
            result = panel.run_panelist_callback(
                "biologist",
                {
                    "callback": {
                        "callback_type": "literature",
                        "assigned_gap": "Need more supporting papers.",
                    },
                    "round_number": 1,
                },
            )

        mock_build_registry.assert_called_once_with(
            role="biologist",
            retriever=panel.retriever,
            judge=panel.judge,
            paper_md_writer=panel.paper_md_writer,
        )
        mock_single_llm_call.assert_not_called()
        self.assertEqual(len(panel.runner_calls), 1)
        self.assertEqual(panel.runner_calls[0]["role"], "biologist")
        self.assertTrue(result["gap_resolved"])

    def test_canonical_literature_type_is_idempotent(self):
        panel = _RoutingProbePanel()

        with patch(
            "agents.scientist_panel.build_panelist_tool_registry",
            return_value="FAKE_REGISTRY",
        ) as mock_build_registry, patch(
            "agents.scientist_panel.single_llm_call"
        ) as mock_single_llm_call:
            panel.run_panelist_callback(
                "statistician",
                {
                    "callback": {
                        "callback_type": "ask_panelist_for_more_literature",
                        "assigned_gap": "Need more supporting papers.",
                    },
                    "round_number": 1,
                },
            )

        mock_build_registry.assert_called_once()
        mock_single_llm_call.assert_not_called()
        self.assertEqual(len(panel.runner_calls), 1)

    def test_reasoning_alias_still_uses_plain_llm_branch(self):
        panel = _RoutingProbePanel()

        with patch(
            "agents.scientist_panel.build_panelist_tool_registry"
        ) as mock_build_registry, patch(
            "agents.scientist_panel.single_llm_call",
            return_value='<CALLBACK>{"gap_resolved": true}</CALLBACK>',
        ) as mock_single_llm_call:
            result = panel.run_panelist_callback(
                "bioinformatician",
                {
                    "callback": {
                        "callback_type": "reasoning",
                        "assigned_gap": "Clarify the statistical unit.",
                    },
                    "round_number": 1,
                },
            )

        mock_build_registry.assert_not_called()
        mock_single_llm_call.assert_called_once()
        self.assertEqual(panel.runner_calls, [])
        self.assertTrue(result["gap_resolved"])


if __name__ == "__main__":
    unittest.main()
