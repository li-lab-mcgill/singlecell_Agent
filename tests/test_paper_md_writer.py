from __future__ import annotations

import unittest
from dataclasses import dataclass

from agents.paper_md_writer import _find_duplicate_wiki_paper, _render_md


@dataclass
class _Node:
    paper_id: str
    title: str
    metadata: dict


class _Index:
    def __init__(self, nodes):
        self._papers = {node.paper_id: node for node in nodes}


class PaperMDWriterTests(unittest.TestCase):
    def test_find_duplicate_wiki_paper_matches_preprint_published_title(self):
        index = _Index(
            [
                _Node(
                    paper_id="benchmarking_joint_integration_2023",
                    title="Benchmarking algorithms for joint integration of unpaired and paired single-cell RNA-seq and ATAC-seq data.",
                    metadata={"doi": "10.1101/2023.02.01.526609", "source_ids": {"doc_id": "pmc:9915567"}},
                )
            ]
        )

        duplicate = _find_duplicate_wiki_paper(
            index,
            {
                "doc_id": "pmc:10594700",
                "title": "Benchmarking algorithms for joint integration of unpaired and paired single-cell RNA-seq and ATAC-seq data.",
                "doi": "10.1186/s13059-023-03073-x",
            },
        )

        self.assertEqual(duplicate, "benchmarking_joint_integration_2023")

    def test_find_duplicate_wiki_paper_matches_normalized_doi(self):
        index = _Index(
            [
                _Node(
                    paper_id="paper_a",
                    title="Paper A",
                    metadata={"doi": "10.1186/example", "source_ids": {}},
                )
            ]
        )

        duplicate = _find_duplicate_wiki_paper(
            index,
            {"title": "Different title", "doi": "https://doi.org/10.1186/example"},
        )

        self.assertEqual(duplicate, "paper_a")

    def test_render_md_uses_curated_paper_sections_only(self):
        md = _render_md(
            payload={
                "doi": "10.1/test",
                "url": "https://example.org",
                "source_ids": {"doc_id": "pmc:1"},
                "full_text_status": "pmc_xml",
                "tasks": ["multiomic_integration"],
                "retrieval_goals": ["evidence_pattern"],
                "retrieval_intents": ["intent"],
                "extends": [],
                "summary": "Summary text.",
                "background": "Background text.",
                "method_and_dataset": "Dataset text.",
                "analysis": "Analysis text.",
                "benchmark_methods": "Benchmark text.",
                "key_findings": "Finding text.",
                "limitations": "Limitation text.",
                "metrics_used": "Metric text.",
                "figure_captions": "Caption text.",
            },
            paper_id="paper_1",
            title="Paper 1",
            session="S001",
        )

        for heading in (
            "## Summary",
            "## Background",
            "## Method and dataset",
            "## Analysis",
            "## Benchmark methods",
            "## Key findings",
            "## Limitations",
            "## Metrics used",
            "## Figure captions",
        ):
            self.assertIn(heading, md)
        self.assertNotIn("## Hypothesis framed", md)
        self.assertNotIn("## Questions answered", md)
        self.assertNotIn("## Boundary conditions", md)


if __name__ == "__main__":
    unittest.main()
