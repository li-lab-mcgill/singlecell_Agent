import unittest

from prompts import literature_prompts as p


LITERATURE_SUMMARY_KEYS = {
    "title",
    "published",
    "abstract",
    "methods",
    "results",
    "discussion",
    "figure_captions",
}


class LiteraturePromptContractTests(unittest.TestCase):
    def test_literature_prompts_format_contract(self):
        fill = {k: "x" for k in LITERATURE_SUMMARY_KEYS}
        p.LITERATURE_SUMMARY_PROMPT.format(**fill)
        p.RAG_CONTEXT_PAPER_SUMMARY.format(**fill)
        self.assertTrue(p.LITERATURE_SUMMARY_SYSTEM.strip())


if __name__ == "__main__":
    unittest.main()
