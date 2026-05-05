---
type: task
id: rna_cell_type_annotation
modality: rna
label: RNA Cell Type Annotation
eval_weights:
  annotation_accuracy: 0.5
  marker_consistency: 0.5
---
Assigns cell type labels to clusters or individual cells in a scRNA-seq dataset. Produces `adata.obs["cell_type"]` with biologically interpretable labels.

This task builds on rna_clustering. If clusters are already available in the adata object, the pipeline can start from the annotate stage.

Stages (in order):
- [[stages/qc]] [includes]
- [[stages/normalize]] [includes]
- [[stages/feature_selection]] [includes]
- [[stages/embed]] [includes]
- [[stages/cluster]] [includes]
- [[stages/project]] [includes]
- [[stages/annotate]] [includes]

Evaluated by:
- [[tools/eval_annotation_accuracy]] [evaluated_by]

Key decisions for the consultant:
- **CellTypist** (default for immune cells): fast, high accuracy for PBMCs and immune tissues; use `majority_voting=True`
- **GPT-4**: use for non-immune tissues, novel cell types, or when CellTypist confidence is low (<0.5)
- **Marker-based**: use when user provides a custom marker gene list or when automated methods disagree
- If batch_key is present: run batch integration before annotation to prevent batch-specific cluster artifacts
- Model selection for CellTypist: `Immune_All_Low.pkl` for fine-grained immune, `Pan_Fetal_Human.pkl` for fetal tissues
