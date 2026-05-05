---
type: stage
id: grn_inference
label: Gene Regulatory Network Inference
---

The GRN inference stage reconstructs regulatory relationships between transcription factors and their target genes. It produces a directed network where edges represent putative regulatory interactions.

Three evidence sources used in different methods:
- **Co-expression**: genes correlated with TF expression across cells (GENIE3, GRNBoost2 in pySCENIC)
- **Motif support**: peaks near target genes contain TF binding motifs (pySCENIC ctx step, SnapATAC2 motif)
- **Footprinting**: TF-specific nucleotide-level depletion pattern in ATAC signal (pycisTopic, HINT-ATAC)
- **Prior knowledge + activity**: statistical deconvolution of expression using curated TF–gene networks (decoupler with CollecTRI)

For RNA-only: decoupler (fast, footprint-free) or pySCENIC (co-expression + motif validation, more comprehensive).
For ATAC or multi-omic: pySCENIC with ATAC peaks as cis-regulatory evidence, or SnapATAC2's integrated motif–gene linking.

Edges:
- [[methods/coexpression_grn]] modality: rna, multi
- [[methods/footprint_grn]] modality: atac, multi
- [[methods/prior_knowledge_grn]] modality: rna, atac, multi
