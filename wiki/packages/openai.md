---
type: package
id: openai
version: ">=1.0"
citation: OpenAI 2023
---

The OpenAI Python SDK provides access to GPT-4 and GPT-4o for LLM-based cell type annotation. It is used by the `rna_annotate_gpt4` tool when CellTypist models do not cover the tissue type or when the user requests manual review.

Install: `pip install openai`

Key usage in single-cell annotation:

```python
from openai import OpenAI
client = OpenAI()  # reads OPENAI_API_KEY from environment

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are an expert in single-cell biology..."},
        {"role": "user", "content": f"Top marker genes for this cluster: {marker_list}. What cell type is this?"}
    ]
)
cell_type = response.choices[0].message.content
```

Requires `OPENAI_API_KEY` environment variable. The pipeline never hardcodes API keys.

GPT-4 annotation is most useful for: (1) non-immune tissues where CellTypist models are absent, (2) rare or novel cell types not in existing atlases, (3) generating human-readable annotation rationale alongside the label.

Key limitation: GPT-4 may hallucinate cell types that do not exist in the dataset. Always validate LLM annotations against marker gene expression before accepting them.
