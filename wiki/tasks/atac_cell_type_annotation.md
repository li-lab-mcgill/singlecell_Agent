---
type: task
id: atac_cell_type_annotation
modality: atac
label: ATAC Cell Type Annotation
eval_weights:
  annotation_accuracy: 1.0
---
Assigns cell type labels to ATAC clusters based on chromatin accessibility patterns. ATAC annotation is more challenging than RNA annotation because canonical marker genes are indirect — accessibility at gene promoters or known regulatory elements must be used as proxies.

Stages (in order):
- [[stages/qc]] [includes]
- [[stages/peak_calling]] [includes]
- [[stages/feature_selection]] [includes]
- [[stages/embed]] [includes]
- [[stages/cluster]] [includes]
- [[stages/project]] [includes]
- [[stages/annotate]] [includes]

Evaluated by:
- [[tools/eval_annotation_accuracy]] [evaluated_by]

Key decisions for the consultant:
- **Gene activity score**: compute a pseudo-RNA profile by summing ATAC signal in gene body + promoter regions → then apply CellTypist or GPT-4 annotation on this pseudo-expression matrix
- **GPT-4 on accessible regions**: for clusters without RNA reference, list the top DA peaks and their nearest genes, then ask GPT-4 for annotation
- **Label transfer from RNA**: if a paired or same-tissue RNA dataset exists, project ATAC cells onto RNA embedding and transfer labels
- LLM-based annotation (GPT-4) is often more practical for ATAC because no pretrained ATAC-specific classifiers exist for most tissues
