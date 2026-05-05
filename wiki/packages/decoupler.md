---
type: package
id: decoupler
version: ">=1.6"
citation: Badia-i-Mompel et al. 2022 Bioinformatics
---

decoupler-py is a framework for running footprint-based gene regulatory network (GRN) inference and pathway activity estimation. It provides a unified interface to multiple statistical methods that estimate transcription factor (TF) or pathway activity from gene expression data using prior knowledge networks.

Install: `pip install decoupler`

Key capabilities:

- **TF activity inference**: `decoupler.run_ulm()` (Univariate Linear Model), `decoupler.run_wmean()` (weighted mean), `decoupler.run_mlm()` (Multivariate Linear Model) — all accept a gene expression matrix and a regulon network
- **Pathway activity**: same methods with MSigDB or PROGENy gene sets as input
- **Prior knowledge**: `decoupler.get_collectri()` — downloads CollecTRI TF-gene network; `decoupler.get_progeny()` — downloads PROGENy pathway gene sets; `decoupler.get_dorothea()` — downloads DoRothEA TF regulons (legacy)
- **Benchmarking**: `decoupler.benchmark()` — compares methods on perturbation datasets

For TF activity, the recommended method is `run_ulm()` with CollecTRI network. Results are stored in `adata.obsm["ulm_estimate"]` and `adata.obsm["ulm_pvals"]`.

Decoupler separates the statistical method from the prior knowledge network, enabling fair comparisons between methods. [Badia-i-Mompel et al. 2022]
