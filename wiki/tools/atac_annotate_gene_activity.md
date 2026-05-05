---
type: tool
id: atac_annotate_gene_activity
stage: annotate
modality: atac
backend: backend/tools/atac/annotate/gene_activity.py
---

Computes a gene activity score for each gene by summing ATAC signal within the gene body and promoter region (typically ±2 kb of TSS). The resulting pseudo-expression matrix enables RNA annotation tools (CellTypist, GPT-4) to be applied to ATAC data.

Key parameters:
- `genome` (default "hg38"): reference genome for gene coordinates; "hg38", "hg19", "mm10", "mm39"
- `upstream` (default 2000): base pairs upstream of TSS to include
- `downstream` (default 0): base pairs downstream of TES to include
- `layer` (default "counts"): peak count layer for signal aggregation

Output stored in `adata.obsm["gene_activity"]` as a (cells × genes) matrix, or in a separate AnnData object. This can then be passed to `rna_annotate_celltypist` or `rna_annotate_gpt4` for annotation.

Note: gene activity scores are a rough proxy for expression — they correlate with RNA but are noisy. Annotation confidence is lower than for actual RNA data.

Package: [[packages/snapatac2]]
Method: [[methods/reference_based_annotation]]
