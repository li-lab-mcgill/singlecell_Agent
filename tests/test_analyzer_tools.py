from __future__ import annotations

import base64
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agents.analyzer_tools import InterpretFigureTool


class _FakeResponses:
    """Captures the `input` kwarg passed to responses.create without making a network call."""

    def __init__(self, output_text: str = '{"description": "ok"}'):
        self._output_text = output_text
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeResponse(self._output_text)


class _FakeResponse:
    def __init__(self, output_text: str):
        self.output_text = output_text
        self.output = []


class _FakeClient:
    def __init__(self):
        self.responses = _FakeResponses()


class InterpretFigureResponsesSchemaTest(unittest.TestCase):
    """Task 3.2: interpret_figure must use Responses-API content part schema.

    The Responses API (`client.responses.create`) rejects Chat-Completions-style
    content parts (`{"type": "text", ...}` / `{"type": "image_url", "image_url":
    {"url": ...}}`) with a 400 error. The correct schema uses `input_text` /
    `input_image` part types, with `image_url` as a plain string and `detail`
    as a sibling field.
    """

    def _make_tool_and_call(self) -> dict:
        client = _FakeClient()
        tool = InterpretFigureTool(client=client, engine_name="gpt-4o")
        with TemporaryDirectory() as tmp:
            fig_path = Path(tmp) / "umap.png"
            # Doesn't need to be a real PNG — run() just base64-encodes the bytes.
            fig_path.write_bytes(b"\x89PNG\r\n\x1a\nfake-image-bytes")
            result = tool.run(figure_path=str(fig_path), context="UMAP colored by cluster")

        self.assertEqual(len(client.responses.calls), 1)
        call_kwargs = client.responses.calls[0]
        self.assertNotIn("error", result, msg=f"interpret_figure returned an error: {result}")
        return call_kwargs

    def test_content_parts_use_responses_api_schema(self):
        call_kwargs = self._make_tool_and_call()

        messages = call_kwargs["input"]
        self.assertEqual(len(messages), 1)
        message = messages[0]
        self.assertEqual(message["role"], "user")

        content = message["content"]
        self.assertEqual(len(content), 2)
        text_part, image_part = content

        # Text part: Responses API uses "input_text", not Chat Completions' "text".
        self.assertEqual(text_part["type"], "input_text")
        self.assertIn("text", text_part)
        self.assertIsInstance(text_part["text"], str)

        # Image part: Responses API uses "input_image"; image_url is a plain
        # string data URI (NOT a nested {"url": ...} object as in Chat
        # Completions), and "detail" is a sibling field.
        self.assertEqual(image_part["type"], "input_image")
        self.assertIsInstance(image_part["image_url"], str)
        self.assertTrue(image_part["image_url"].startswith("data:"))
        self.assertIn("detail", image_part)
        self.assertNotIsInstance(image_part["image_url"], dict)

    def test_mime_type_and_base64_payload_embedded_in_data_uri(self):
        call_kwargs = self._make_tool_and_call()
        image_part = call_kwargs["input"][0]["content"][1]
        self.assertTrue(image_part["image_url"].startswith("data:image/png;base64,"))
        b64_payload = image_part["image_url"].split(",", 1)[1]
        self.assertEqual(base64.standard_b64decode(b64_payload), b"\x89PNG\r\n\x1a\nfake-image-bytes")

    def test_run_does_not_swallow_success_into_vlm_call_failed(self):
        """Regression guard: the old Chat-Completions shape triggered a 400 that the
        surrounding `except Exception` turned into {"error": "VLM call failed: ..."}."""
        client = _FakeClient()
        tool = InterpretFigureTool(client=client, engine_name="gpt-4o")
        with TemporaryDirectory() as tmp:
            fig_path = Path(tmp) / "fig.png"
            fig_path.write_bytes(b"fake-bytes")
            result = tool.run(figure_path=str(fig_path), context="context")

        self.assertNotIn("error", result)
        self.assertEqual(result, {"description": "ok"})


if __name__ == "__main__":
    unittest.main()
