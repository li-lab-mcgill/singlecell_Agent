---
type: stage
id: peak_to_gene
label: Peak-to-Gene Linkage
---

The peak-to-gene linkage stage connects distal regulatory elements (ATAC peaks) to their putative target genes using co-accessibility or correlation between chromatin accessibility and gene expression. This is a key step for understanding cis-regulatory logic.

This stage requires paired RNA+ATAC data (10x Multiome or SHARE-seq) to compute accessibility–expression correlations. For ATAC-only data, distance-based linking is the fallback.

Output: a table of (peak, gene, correlation, p-value) triplets, which can be visualized as a regulatory network or used to prioritize regulatory elements for downstream motif analysis.

Edges:
- [[methods/correlation_peak2gene]] modality: multi
- [[methods/distance_peak2gene]] modality: atac, multi
