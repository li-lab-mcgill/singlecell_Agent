---
type: task
id: multi_cell_type_annotation
modality: multi
label: Multi-omic Cell Type Annotation
eval_weights:
  annotation_accuracy: 1.0
---
Annotates cell types using both RNA and ATAC information. Joint annotation leverages corroborating evidence from chromatin accessibility and gene expression, producing more confident labels.

Stages (in order):
- [[stages/qc]] [includes]
- [[stages/normalize]] [includes]
- [[stages/feature_selection]] [includes]
- [[stages/peak_calling]] [includes]
- [[stages/intersect]] [includes]
- [[stages/embed]] [includes]
- [[stages/cluster]] [includes]
- [[stages/project]] [includes]
- [[stages/annotate]] [includes]

Evaluated by:
- [[tools/eval_annotation_accuracy]] [evaluated_by]

Key decisions for the consultant:
- **RNA-first annotation**: annotate using CellTypist on the RNA modality, then validate against ATAC accessibility at marker gene loci
- **Joint evidence**: use gene activity scores (ATAC signal at gene promoters) as a secondary confirmation for RNA-based labels
- **GPT-4**: provide both top DE genes AND top DA peaks as evidence; ask for annotation with rationale
- Label assignments should be written to `mdata.obs["cell_type"]` and propagated to both modality AnnData objects
