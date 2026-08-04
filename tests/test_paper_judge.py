"""Tests for agents/paper_judge.py::_parse_verdict robustness.

_parse_verdict() turns the raw LLM verdict text into a structured dict via a
direct json.loads() parse. If that parse (or the dict-building that follows
it) raises for ANY reason, the whole `except Exception: pass` swallows it and
falls through to a much weaker regex-extraction fallback that cannot recover
most fields (evidence_contribution, covered_evidence_patterns, etc. all come
back blank/empty).

Two payload shapes previously triggered this silently-lossy fallback even
though the JSON was perfectly well-formed and the paper was relevant:

1. `"confidence": null` -- the key IS present, so `payload.get("confidence",
   0.0)` returns None (the default is only used when the key is absent), and
   `float(None)` raises TypeError. A genuinely relevant paper's structured
   verdict (with its evidence_contribution etc.) was discarded, and the
   regex-fallback confidence of 0.0 would then fail the judge's cutoff.
2. `"relevant": "false"` (a stringified bool) -- `bool("false")` is True,
   because any non-empty string is truthy in Python, so an explicitly
   negative verdict was flipped to relevant=True.

These tests pin _parse_verdict to tolerate both cases without losing the
structured fields.
"""

from __future__ import annotations

import unittest

from agents.paper_judge import _parse_verdict


class ParseVerdictNullConfidenceTests(unittest.TestCase):
    def test_null_confidence_keeps_structured_dict(self):
        payload = (
            '{"relevant": true, "confidence": null, '
            '"evidence_contribution": "strong TF evidence", '
            '"covered_evidence_patterns": []}'
        )
        verdict = _parse_verdict(payload)

        self.assertTrue(verdict["relevant"])
        self.assertEqual(verdict["confidence"], 0.0)
        # This is the tell: the regex fallback always blanks
        # evidence_contribution to "". If we see the real string here, the
        # structured JSON branch produced this verdict (not the fallback).
        self.assertEqual(verdict["evidence_contribution"], "strong TF evidence")

    def test_stringy_relevant_false_is_false(self):
        payload = (
            '{"relevant": "false", "confidence": 0.9, '
            '"evidence_contribution": "irrelevant"}'
        )
        verdict = _parse_verdict(payload)

        self.assertFalse(verdict["relevant"])

    def test_stringy_relevant_true_is_true(self):
        payload = '{"relevant": "true", "confidence": 0.5}'
        verdict = _parse_verdict(payload)

        self.assertTrue(verdict["relevant"])

    def test_non_numeric_confidence_string_falls_back_to_default(self):
        payload = '{"relevant": true, "confidence": "high", "evidence_contribution": "x"}'
        verdict = _parse_verdict(payload)

        self.assertTrue(verdict["relevant"])
        self.assertEqual(verdict["confidence"], 0.0)
        self.assertEqual(verdict["evidence_contribution"], "x")

    def test_well_formed_numeric_confidence_still_works(self):
        payload = '{"relevant": true, "confidence": 0.82, "evidence_contribution": "y"}'
        verdict = _parse_verdict(payload)

        self.assertTrue(verdict["relevant"])
        self.assertEqual(verdict["confidence"], 0.82)
        self.assertEqual(verdict["evidence_contribution"], "y")


if __name__ == "__main__":
    unittest.main()
