---
type: tool
id: rna_annotate_gpt4
stage: annotate
modality: rna
backend: backend/tools/rna/annotate/gpt4.py
---

Annotates cell clusters by sending top marker genes to GPT-4 and parsing the returned cell type labels with reasoning.

Key parameters:
- `cluster_key` (default "leiden_clusters"): which cluster column to annotate
- `n_top_genes` (default 15): number of top marker genes per cluster to include in the prompt
- `tissue` (default None): tissue context string added to the prompt (e.g., "human PBMC", "mouse liver"); strongly recommended for accuracy
- `species` (default "human"): species context
- `model` (default "gpt-4o"): OpenAI model to use
- `label_key` (default "gpt4_cell_type"): `adata.obs` column to store predicted labels

Requires `OPENAI_API_KEY` environment variable. Runs `sc.tl.rank_genes_groups()` internally if not already done.

Outputs:
- `adata.obs["gpt4_cell_type"]`: per-cluster label (same label for all cells in a cluster)
- `adata.uns["gpt4_annotation"]`: dict with per-cluster label, confidence, marker evidence, and reasoning

Always validate GPT-4 outputs by checking that the stated markers are actually highly expressed in the cluster using a dot plot.

Package: [[packages/openai]]
Method: [[methods/llm_based_annotation]]
