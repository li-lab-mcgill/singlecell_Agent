---
type: stage
id: annotate
label: Cell Type Annotation
---

The annotation stage assigns biological cell type labels to clusters or individual cells. It is performed after clustering and uses marker genes (RNA) or chromatin accessibility patterns (ATAC) as evidence.

Three annotation strategies exist with different tradeoffs:
- **Marker-based**: manual or rule-based; high precision but requires domain expertise
- **Reference-based**: automated using pretrained models (CellTypist) or label transfer; fast but limited to tissues in the training data
- **LLM-based**: GPT-4 interprets marker gene lists; flexible and tissue-agnostic but requires validation

For immune cells, CellTypist with majority voting is the recommended default. For non-immune or novel tissues, LLM-based annotation followed by manual curation is preferred.

Edges:
- [[methods/marker_based_annotation]] modality: rna, multi
- [[methods/reference_based_annotation]] modality: rna, multi
- [[methods/llm_based_annotation]] modality: rna, atac, multi
