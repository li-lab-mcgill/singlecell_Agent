---
type: method
id: llm_based_annotation
label: LLM-based Cell Type Annotation
---

LLM-based annotation uses a large language model (GPT-4) to interpret cluster marker gene lists and propose cell type labels with biological reasoning. It is tissue-agnostic and works without a pretrained classifier.

Workflow:
1. Run `sc.tl.rank_genes_groups()` to get top N marker genes per cluster
2. Format a structured prompt: tissue context, top N markers per cluster, species
3. Call GPT-4 API; parse returned cell type labels and reasoning
4. Store labels in `adata.obs["gpt4_cell_type"]` with per-cluster confidence notes

Prompt design is critical. The prompt should include:
- Tissue type and experimental context
- Species
- Top 10–20 marker genes per cluster (sorted by log fold change or score)
- Instruction to provide a primary label, confidence (high/medium/low), and marker evidence

LLM annotation is best for:
- Non-immune tissues where CellTypist models are absent
- Novel or rare cell types not in reference atlases
- Generating human-readable annotation rationale

Key limitation: GPT-4 may confabulate cell types. Always validate by checking that stated markers are actually highly expressed in the cluster. Do not use LLM annotations without expression-level validation.

Requires `OPENAI_API_KEY` in environment.

Edges:
- [[tools/rna_annotate_gpt4]] implements
