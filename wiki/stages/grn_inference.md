---
type: stage
id: grn_inference
label: Gene Regulatory Network Inference
---

The GRN inference stage reconstructs regulatory relationships between transcription factors and their target genes. It produces a directed network where edges represent putative regulatory interactions.

Three evidence sources used in different methods:
- **Co-expression**: genes correlated with TF expression across cells (GENIE3, GRNBoost2 in pySCENIC)
- **Motif support**: peaks near target genes contain TF binding motifs (pySCENIC ctx step, SnapATAC2 motif)
- **Footprinting**: TF-specific nucleotide-level depletion pattern in ATAC signal (HINT-ATAC)
- **Topic modeling + motif enrichment**: LDA decomposition of ATAC peaks into co-accessible topics; TF motifs enriched in topic region sets (pycisTopic + pycistarget, used in SCENIC+)
- **Prior knowledge + activity**: statistical deconvolution of expression using curated TF–gene networks (decoupler with CollecTRI)

For RNA-only: decoupler (fast, footprint-free) or pySCENIC (co-expression + motif validation, more comprehensive).
For paired scRNA + scATAC: SCENIC+ (enhancer-driven eRegulons integrating motif enrichment, peak-gene correlation, and co-expression), or pySCENIC with ATAC peaks as cis-regulatory evidence.

Edges:
- [[methods/coexpression_grn]] modality: rna, multi
- [[methods/prior_knowledge_grn]] modality: rna, atac, multi
- [[methods/enhancer_grn]] modality: multi
