---
type: package
id: scenicplus
version: ">=1.0"
citation: Bravo González-Blas et al. 2023 Nature Methods
---

SCENIC+ (Single-Cell ENhancer-driven gene regulatory network Inference using ATAC and RNA data) infers enhancer-driven gene regulatory networks (eGRNs) from paired scRNA-seq + scATAC-seq data. It produces eRegulons: triplets of `(TF, regulatory_regions, target_genes)` with directionality and multi-modal activity scores.

Install: `pip install scenicplus`

## Key concepts

**eRegulon**: A TF together with its regulatory regions (peaks with TF binding motifs) and the target genes linked to those regions. Each eRegulon has a direction: activating (rho > 0) or repressing (rho < 0).

**Three evidence layers** integrated in eGRN inference:
1. TF binding motif enrichment in accessible regions (via pycistarget)
2. Peak → gene correlation + importance (Spearman + random forest)
3. TF → gene co-expression (GRNBoost2)

## Serialization

SCENICPLUS objects must be serialized with `dill`, not `pickle`:
```python
import dill
with open(path, "wb") as f:
    dill.dump(scplus_obj, f)
```

## Key functions

| Function | Module | Purpose |
|---|---|---|
| `create_SCENICPLUS_object()` | `scenicplus.scenicplus_class` | Construct object from RNA + ATAC |
| `merge_cistromes()` | `scenicplus.cistromes` | Convert menr to cistrome AnnDatas (required before build_grn) |
| `build_grn()` | `scenicplus.grn_builder.gsea_approach` | GSEA-based eRegulon inference |
| `format_egrns()` | `scenicplus.utils` | Convert eRegulon list to metadata DataFrame |
| `get_eRegulons_as_signatures()` | `scenicplus.eregulon_enrichment` | Convert metadata to signature dicts |
| `make_rankings()` | `scenicplus.eregulon_enrichment` | Build AUCell rankings for scoring |
| `score_eRegulons()` | `scenicplus.eregulon_enrichment` | AUCell scoring (call twice: region + gene) |
| `get_search_space()` | `scenicplus.data_wrangling.gene_search_space` | Define candidate peak-gene pairs |
| `calculate_regions_to_genes_relationships()` | `scenicplus.enhancer_to_gene` | Importance + correlation scoring |
| `run_pycistarget()` | `scenicplus.wrappers.run_pycistarget` | SCENIC+ wrapper for pycistarget |

## Parallelism

SCENIC+ uses Ray for internal parallelism. The relevant parameter is `ray_n_cpu`, not `n_cpu`.

## AUCell scoring

`score_eRegulons()` must be called **twice** — once for `enrichment_type='region'` and once for `enrichment_type='gene'`. Results accumulate under `scplus_obj.uns["eRegulon_AUC"]["Region_based"]` and `["Gene_based"]`.

Used by: [[tools/multi_grn_scenicplus]], [[tools/multi_grn_scenicplus_aucell]], [[tools/multi_grn_peak_to_gene]], [[tools/multi_grn_pycistarget]]
