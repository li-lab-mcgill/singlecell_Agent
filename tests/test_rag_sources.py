import os
import sys
import types
import unittest
from unittest.mock import patch

if "requests" not in sys.modules:
    fake_requests = types.ModuleType("requests")

    class _FakeResponse:
        def __init__(self):
            self.status_code = 200

    class _FakeHTTPError(Exception):
        def __init__(self, message="", response=None):
            super().__init__(message)
            self.response = response

    class _FakeSession:
        def get(self, *args, **kwargs):
            raise NotImplementedError

    fake_requests.Response = _FakeResponse
    fake_requests.HTTPError = _FakeHTTPError
    fake_requests.ConnectionError = type("ConnectionError", (Exception,), {})
    fake_requests.Timeout = type("Timeout", (Exception,), {})
    fake_requests.Session = _FakeSession
    sys.modules["requests"] = fake_requests

import requests

from rag_sources import _finalize_sections, normalize_section_type, resolve_pmcid_for_pubmed
from rag_types import RAGSection


class RagSourcesTests(unittest.TestCase):
    def test_finalize_sections_makes_duplicate_abstract_ids_unique(self):
        sections = _finalize_sections(
            [
                RAGSection(section_id="abstract:lead", section_type="abstract", heading="Abstract", text="Lead abstract", order=-1),
                RAGSection(section_id="abstract:0", section_type="abstract", heading="Abstract", text="XML abstract", order=0),
            ]
        )
        self.assertEqual([section.section_id for section in sections], ["abstract:0", "abstract:1"])

    def test_normalize_section_type_maps_methods(self):
        self.assertEqual(normalize_section_type("Materials and Methods"), "methods")

    def test_normalize_section_type_maps_discussion(self):
        self.assertEqual(normalize_section_type("Discussion"), "discussion")

    @patch("rag_sources._retry_get")
    def test_resolve_pmcid_for_pubmed_returns_empty_on_rate_limit(self, mock_retry_get):
        response = requests.Response()
        response.status_code = 429
        mock_retry_get.side_effect = requests.HTTPError("rate limited", response=response)
        with patch.dict(os.environ, {"NCBI_EMAIL": "test@example.com"}, clear=False):
            self.assertEqual(resolve_pmcid_for_pubmed("36583014"), "")


if __name__ == "__main__":
    unittest.main()
