---
type: package
id: pyscenic
version: ">=0.12"
citation: Aibar et al. 2017 Nature Methods; Van de Sande et al. 2020 Nature Protocols
---

pySCENIC is a Python implementation of the SCENIC algorithm for single-cell gene regulatory network inference. It infers transcription factor regulons from co-expression patterns and validates them against cis-regulatory motif databases.

Install: `pip install pyscenic`

pySCENIC runs in three stages:

1. **GRN inference**: `pyscenic grn` — co-expression modules via GRNBoost2 or GENIE3; requires expression matrix and a list of TF names; outputs adjacency matrix
2. **Regulon pruning**: `pyscenic ctx` — prunes modules using motif enrichment analysis against cisTarget databases; outputs regulons (TF + target genes with motif support)
3. **AUC scoring**: `pyscenic aucell` — scores each cell for regulon activity using AUCell; outputs regulon activity matrix stored in `adata.obsm["X_pyscenic_auc"]`

Required databases (download separately):
- TF list: `allTFs_hg38.txt` or `allTFs_mm10.txt`
- Motif rankings: `hg38__refseq-r80__10kb_up_and_down_tss.mc9nr.feather` (standard v9 preset)
- Motif annotations: `motifs-v9-nr.hgnc-m0.001-o0.0.tbl`

See [[resources/pyscenic_databases]] for the full file list and download utility.

pySCENIC is the most validated single-cell GRN method but requires significant compute (GRNBoost2 step). For large datasets, run the GRN step on a cluster. The AUCell step is memory-efficient and fast. [Aibar et al. 2017]

## AUCell stage (stage 3)

`pyscenic aucell` scores each cell for regulon activity. In this system, AUCell is run by `rna_grn_pyscenic_aucell` as a separate step after `rna_grn_pyscenic`. This allows re-scoring with different thresholds without re-running the expensive GRN inference.

Output: `adata.obsm["X_pyscenic_auc"]` (cells × TF regulons; numpy array) with column names in `adata.uns["pyscenic_auc_tf_names"]`.
