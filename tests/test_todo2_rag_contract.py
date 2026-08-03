from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agents.paper_judge import _apply_confidence_policy, _parse_verdict
from rag.literature_retriever import _deduplicate_documents
from rag.types import RAGDocument
from wiki.paper_index import PaperWikiIndex


class Todo2RagContractTests(unittest.TestCase):
    def test_paper_judge_parses_evidence_fit_schema(self) -> None:
        verdict = _parse_verdict(
            """
            {
              "relevant": true,
              "confidence": 0.91,
              "reason": "Direct match.",
              "evidence_contribution": "Defines T cells and compares disease/control abundance.",
              "covered_evidence_patterns": ["entity_definition", "comparison_design", "claim_supported"],
              "missing_evidence": ["No donor random effect"],
              "suggested_query_terms": ["mixed effects model"],
              "suggested_exclusions": ["TCR only"]
            }
            """
        )
        self.assertTrue(verdict["relevant"])
        self.assertEqual(verdict["covered_evidence_patterns"], ["entity_definition", "comparison_design"])
        self.assertEqual(verdict["missing_evidence"], ["No donor random effect"])

    def test_abstract_only_confidence_cap_for_evidence_patterns(self) -> None:
        verdict = {
            "relevant": True,
            "confidence": 0.95,
            "reason": "Looks relevant.",
            "missing_evidence": [],
        }
        capped = _apply_confidence_policy(
            verdict,
            paper={"full_text_status": "abstract_only"},
            retrieval_goal="evidence_pattern",
        )
        self.assertEqual(capped["confidence"], 0.70)
        self.assertTrue(capped["missing_evidence"])

    def test_literature_dedup_prefers_full_text_by_doi(self) -> None:
        abstract = RAGDocument(
            doc_id="semantic_scholar:s1",
            source="semantic_scholar",
            source_id="s1",
            title="Shared paper",
            text="abstract",
            abstract="abstract",
            doi="10.1/shared",
            metadata={"full_text_status": "abstract_only", "s2_paper_id": "s1"},
        )
        full_text = RAGDocument(
            doc_id="pmc:123",
            source="pmc",
            source_id="123",
            title="Shared paper",
            text="full text",
            abstract="abstract",
            doi="10.1/shared",
            doc_type="core_full_text",
            metadata={"full_text_status": "pmc_xml", "pmcid": "123"},
        )
        deduped = _deduplicate_documents([abstract, full_text])
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0].doc_id, "pmc:123")
        self.assertEqual(deduped[0].metadata["s2_paper_id"], "s1")

    def test_query_paper_wiki_scopes_by_role_goal_and_intent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            papers_dir = Path(tmp)
            (papers_dir / "paper1.md").write_text(
                """---
paper_id: paper1
title: "Donor-level T cell expansion"
tasks: ["rna_differential_abundance"]
retrieval_goals: ["evidence_pattern"]
retrieval_intents: ["What statistical unit supports T cell expansion?"]
full_text_status: "pmc_xml"
extends: []
added: 2026-05-11
session: test
---

## Summary
This paper uses donor-level mixed models for differential abundance.
""",
                encoding="utf-8",
            )
            index = PaperWikiIndex(papers_dir)
            hits = index.query_papers(
                user_question="Do T cells expand?",
                data_summary="PBMC disease vs healthy",
                role="statistician",
                retrieval_goal="evidence_pattern",
                retrieval_intent="What statistical unit supports T cell expansion?",
                top_k=5,
            )
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["paper_id"], "paper1")
        self.assertEqual(hits[0]["full_text_status"], "pmc_xml")


if __name__ == "__main__":
    unittest.main()
