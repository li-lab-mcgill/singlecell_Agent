---
type: method
id: marker_based_annotation
label: Marker Gene-based Annotation
---

Marker-based annotation assigns cell type labels by comparing cluster-level gene expression to known canonical marker genes. It is the most interpretable annotation method and serves as ground truth for validating automated methods.

Two sub-approaches:

**Differential marker discovery**: `sc.tl.rank_genes_groups()` computes marker genes for each cluster versus all other clusters (or versus a reference group). Top markers per cluster are then matched to known biology manually or with a lookup table.

**Dot plot / heatmap scoring**: a curated list of known markers is provided; expression of each marker per cluster is visualized as a dot plot. Cell types are assigned by pattern recognition.

Key considerations:
- Canonical markers vary by tissue and species — always use tissue-appropriate references
- A single gene is rarely sufficient; use sets of co-expressed markers
- Some markers are shared across related cell types (e.g., CD3 for all T cells); use combinations to distinguish subtypes

Marker genes per cluster are stored in `adata.uns["rank_genes_groups"]`. Cell type assignments should be written to `adata.obs["cell_type"]`.

Edges:
- [[tools/rna_annotate_cellmarker]] implements
