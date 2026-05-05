---
type: stage
id: motif
label: Motif Analysis
---

The motif analysis stage identifies transcription factor binding motifs enriched in accessible peaks. It connects chromatin accessibility patterns to the transcription factors that may regulate them.

Two use cases:
1. **Enrichment in DA peaks**: given a set of differentially accessible peaks, find TF motifs over-represented in those peaks versus background — identifies putative TF regulators of condition-specific accessibility
2. **Motif scanning**: score all peaks against a motif database to create a TF × cell matrix of motif accessibility — used as input for TF activity inference

Motif databases: JASPAR2024 (open-access), HOCOMOCO v12.

Edges:
- [[methods/motif_enrichment]] modality: atac, multi
- [[methods/motif_scanning]] modality: atac, multi
