"""Visual analysis of UMAP PNG images using a multimodal LLM."""
import base64
import os

UMAP_ANALYSIS_SYSTEM = (
    "You are a computational biology expert analyzing UMAP visualizations of "
    "single-cell RNA-seq embeddings. Describe what you observe concisely and "
    "focus on what is actionable for improving the model."
)

UMAP_ANALYSIS_PROMPT = (
    "Analyze this UMAP plot of single-cell embeddings.\n"
    "Describe: (1) cluster separation and compactness, "
    "(2) presence of batch effects or mixing artifacts, "
    "(3) whether cell type structure looks biologically coherent, "
    "(4) any specific issues the model training or clustering should address.\n"
    "Be concise (3-5 sentences). Focus on actionable observations."
)


def _encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


class VisualAnalyzer:
    """Analyze UMAP PNG images with a multimodal API call."""

    def __init__(self, engine_name: str):
        self.engine_name = engine_name
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import openai
            self._client = openai.OpenAI()
            return self._client
        except ImportError:
            raise RuntimeError("openai package required for visual analysis")

    def analyze(self, image_path: str) -> str:
        """Return a text description of the UMAP image, or a fallback string."""
        if not image_path or not os.path.exists(image_path):
            return "<none>"
        try:
            b64 = _encode_image(image_path)
            client = self._get_client()
            vision_model = self._vision_model()
            response = client.chat.completions.create(
                model=vision_model,
                messages=[
                    {"role": "system", "content": UMAP_ANALYSIS_SYSTEM},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": UMAP_ANALYSIS_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{b64}",
                                    "detail": "high",
                                },
                            },
                        ],
                    },
                ],
                max_tokens=400,
                temperature=0.2,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"<umap_analysis_failed: {e}>"

    def _vision_model(self) -> str:
        """Pick a vision-capable model name based on the configured engine."""
        name = self.engine_name.lower()
        if "gpt-5" in name or "gpt-4o" in name:
            return self.engine_name
        if "gpt-4" in name:
            return "gpt-4o"
        return "gpt-4o"
