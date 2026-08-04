from __future__ import annotations

import unittest

from agents.analyzer_panel import _tag_done_handler


class AnalyzerTagDoneHandlerAliasTests(unittest.TestCase):
    """`agents/analyzer_panel.py` has its own `_tag_done_handler` / `_extract_tag_json`
    pair (separate from `agents/mediator_agent.py`'s). `_extract_tag_json` tolerates
    the alias tag ANALYZER_OUTPUT for the canonical ANALYZER tag, but until fixed
    `_tag_done_handler` only recognized the literal canonical tag — so an
    alias-wrapped analyzer response would never satisfy the done-handler and would
    burn through max_iterations before crashing with RuntimeError."""

    def test_alias_tag_is_recognized_as_done(self):
        text = '<ANALYZER_OUTPUT>{"results_summary": "x"}</ANALYZER_OUTPUT>'
        result = _tag_done_handler(text, "ANALYZER")

        self.assertEqual(result, {"done": True, "result": text})

    def test_canonical_tag_is_still_recognized_as_done(self):
        text = '<ANALYZER>{"results_summary": "x"}</ANALYZER>'
        result = _tag_done_handler(text, "ANALYZER")

        self.assertEqual(result, {"done": True, "result": text})

    def test_response_with_no_recognized_tag_is_not_done(self):
        text = "I am still thinking and have not produced a tagged block yet."
        result = _tag_done_handler(text, "ANALYZER")

        self.assertFalse(result["done"])
        self.assertIn("next_user_input", result)


if __name__ == "__main__":
    unittest.main()
