---
type: method
id: coexpression_grn
label: Co-expression-based GRN Inference
---

Co-expression GRN inference builds a TF → target gene network by identifying genes whose expression is correlated with TF expression across cells. It relies solely on expression data without requiring chromatin accessibility.

pySCENIC's GRN step uses GRNBoost2 (gradient boosting-based) to infer TF → gene importance scores, producing a weighted adjacency matrix. This is then pruned in the ctx step using motif enrichment to retain only TF → gene edges with cis-regulatory support.

Standalone co-expression without motif pruning:
- Fast but produces many false positives (indirect co-regulation)
- Useful for exploratory hypothesis generation
- Does not distinguish direct regulation from co-regulated targets

With motif pruning (full pySCENIC):
- More specific — requires both expression correlation AND TF binding evidence
- Produces regulons: TF + co-regulated targets with motif support
- Standard for published GRN analyses

Output: adjacency matrix (for co-expression alone) or regulon dictionary `{TF: [target_genes]}` (full pySCENIC).

Edges:
- [[tools/rna_grn_grnboost2]] implements
- [[tools/rna_grn_pyscenic]] implements
- [[tools/rna_grn_pyscenic_aucell]] implements (AUCell stage)
