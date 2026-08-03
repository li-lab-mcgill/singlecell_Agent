---
type: method
id: prior_knowledge_grn
label: Prior Knowledge-based TF Activity Inference
---

Prior knowledge GRN methods estimate TF activity by statistically deconvolving observed expression using a curated TF → gene network. They do not infer new edges — they score TF activity given known regulatory relationships.

decoupler-py is the primary tool. It provides multiple statistical methods that all take:
- Input: gene expression matrix (cells × genes)
- Prior knowledge: TF → gene network with weights (e.g., CollecTRI, DoRothEA)
- Output: TF activity matrix (cells × TFs)

Recommended method: `run_ulm()` (Univariate Linear Model) with CollecTRI network. CollecTRI is a manually curated, signed TF–target database covering ~1000 human TFs.

Key advantage: fast (minutes vs. hours for pySCENIC), no ATAC data required, interpretable activity scores.

Key limitation: only assesses TFs present in the prior knowledge network; cannot discover novel regulators.

Output: `adata.obsm["ulm_estimate"]` (activity scores) and `adata.obsm["ulm_pvals"]` (significance). TF activity can be visualized on UMAP like any cell embedding.

Edges:
- [[tools/rna_grn_decoupler]] implements
