---
type: method
id: enhancer_grn
label: Enhancer-driven GRN Inference (eGRN)
---

Enhancer-driven GRN inference produces eRegulons: triplets of `(TF, regulatory_regions, target_genes)` that integrate three independent lines of evidence to link a TF to a specific target gene via a specific regulatory element.

## Three evidence layers

1. **TF binding motif enrichment** (chromatin): TF motifs are enriched in open chromatin regions (via cisTarget / pycistarget). This links TFs to regulatory regions.
2. **Region → gene correlation** (multi-modal): open chromatin at a peak correlates with expression of a nearby gene (Spearman correlation + random forest importance). This links regulatory regions to target genes.
3. **TF → gene co-expression** (transcriptomic): TF expression correlates with target gene expression across cells (GRNBoost2). This provides an independent transcriptional validation.

An eRegulon is formed when all three evidence layers converge on the same (TF, region, gene) triplet.

## eGRN vs. co-expression GRN

| Aspect | eGRN (SCENIC+) | Co-expression GRN (pySCENIC) |
|---|---|---|
| Data required | Paired scRNA + scATAC | scRNA only |
| Regulatory resolution | Single enhancer resolution | Gene-level only |
| Directionality | Activating / repressing (via rho sign) | Activating only (importance score) |
| False positive rate | Lower (three evidence layers) | Higher (co-regulation not excluded) |
| Compute | High (multiple steps, Ray parallelism) | Moderate (GRNBoost2 + cisTarget) |

## When to use SCENIC+ over pySCENIC

- Paired scRNA + scATAC data is available (multi-ome or co-assay)
- Enhancer-level regulatory mechanisms are of interest
- Activating vs. repressing TF activity needs to be distinguished
- Dataset is large enough for stable correlations (≥200 cells per condition recommended)

## Pseudoreplication warning

Peak-to-gene correlation treats each cell as an independent observation. For datasets with <5 cells per donor, the correlation step will produce noisy links. Pseudobulk aggregation by sample before correlation is recommended for multi-donor datasets.

## Output: eRegulon metadata DataFrame

Stored in `adata.uns["scenicplus_eregulons"]`. Key columns:
- `Region_signature_name`: `"{TF}_(+|-)_{context}"` — eRegulon identity (region side)
- `Gene_signature_name`: `"{TF}_(+|-)_{context}"` — eRegulon identity (gene side)
- `Region`: peak identifier in `chr:start-end` format
- `Gene`: target gene symbol
- `rho`: Spearman correlation coefficient (sign encodes direction)
- `importance`: random forest importance score
- `importance_x_rho`: composite score (signed; positive = activating)
- `importance_x_abs_rho`: composite score using |rho| (unsigned strength, useful for ranking eRegulons regardless of direction)

Edges:
- [[tools/multi_grn_scenicplus]] implements
- [[tools/multi_grn_scenicplus_aucell]] implements (scoring)
