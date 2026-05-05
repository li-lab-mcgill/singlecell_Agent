---
type: method
id: reference_based_annotation
label: Reference-based Automated Annotation
---

Reference-based annotation uses a pretrained classifier or reference atlas to automatically assign cell type labels to query cells without manual inspection of marker genes.

**CellTypist** is the primary tool. It uses pretrained logistic regression models trained on curated atlases. `majority_voting=True` smooths predictions using cluster membership, reducing noise from low-confidence individual cell predictions.

**Label transfer (scVI)**: train scVI on a reference dataset with known labels, then use the model to annotate a query dataset by projecting query cells into the reference latent space and finding nearest neighbors.

Annotation quality depends heavily on how well the reference matches the query tissue and species. For PBMC immune cells, CellTypist with `Immune_All_Low.pkl` is highly reliable. For non-immune or non-human tissues, confidence scores will be low — switch to LLM-based or manual annotation.

Outputs:
- `adata.obs["celltypist_cell_type"]` — per-cell predicted label
- `adata.obs["celltypist_conf_score"]` — confidence score (0–1)
- `adata.obs["majority_voting"]` — cluster-smoothed label

Always inspect the confidence score distribution. Cells with scores < 0.5 should be flagged for manual review.

Edges:
- [[tools/rna_annotate_celltypist]] implements
