---
type: method
id: highly_variable_genes
label: Highly Variable Gene Selection
---

Highly variable gene (HVG) selection retains genes that vary substantially across cells, discarding housekeeping genes that contribute noise rather than signal to cell-type discrimination.

Standard approach: `sc.pp.highly_variable_genes()` fits a mean-dispersion trend, then selects genes with dispersion above the trend. For multi-batch datasets, use `batch_key` to select HVGs that are variable within each batch, then take the union or intersection.

Key parameters:
- `n_top_genes`: number of HVGs to select; typically 2000–5000; more is not always better
- `flavor`: `"seurat_v3"` (variance-stabilized; recommended for raw counts) or `"cell_ranger"` (log-normalized; older)
- `batch_key`: computes HVGs per batch and takes the intersection of top genes

HVGs are stored as `adata.var["highly_variable"] = True/False`. Downstream PCA automatically subsets to HVGs if `use_highly_variable=True`.

For very small datasets (<5000 cells), the dispersion estimate is noisy — consider using all genes or increasing `n_top_genes`.

Edges:
- [[tools/rna_feature_selection_scanpy_hvg]] implements
- [[tools/rna_feature_selection_seurat_v3]] implements
- [[tools/rna_feature_selection_cellranger]] implements
