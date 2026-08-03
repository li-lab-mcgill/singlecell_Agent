#!/usr/bin/env Rscript
# ---------------------------------------------------------------------------
# Seurat PCA as a stand-alone subprocess job.
#
# Usage (driven by RRunner):
#   Rscript dimreduction_seurat_pca.R --args-json /tmp/args.json
#
# Args JSON keys:
#   input_h5ad   (str) path to input AnnData (.h5ad)
#   output_h5ad  (str) path to write processed AnnData
#   n_pcs        (int) number of PCs (default 50)
#   seed         (int) random seed (default 42)
#   n_features   (int) number of variable features to select (default 2000)
#
# Stdout contract: prints one JSON object on the final line. The Python
# RRunner parses the last valid JSON line.
#
# Dependencies: jsonlite, Seurat (>=4), reticulate, anndata, scipy.
# h5ad I/O is done through anndata so sparse X is preserved on read and
# adata.obs/var/layers are preserved while writing obsm["X_seurat_pca"].
# The reader prefers adata.layers["counts"] and falls back to adata.X.
# ---------------------------------------------------------------------------

suppressPackageStartupMessages({
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
args_json_path <- NULL
for (i in seq_along(args)) {
  if (args[[i]] == "--args-json" && length(args) >= i + 1) {
    args_json_path <- args[[i + 1]]
    break
  }
}
if (is.null(args_json_path)) {
  stop("--args-json <path> is required")
}

params <- jsonlite::fromJSON(args_json_path)
input_h5ad  <- params$input_h5ad
output_h5ad <- params$output_h5ad
n_pcs       <- ifelse(is.null(params$n_pcs), 50L, as.integer(params$n_pcs))
seed        <- ifelse(is.null(params$seed), 42L, as.integer(params$seed))
n_features  <- ifelse(is.null(params$n_features), 2000L, as.integer(params$n_features))

set.seed(seed)

suppressPackageStartupMessages({
  library(Seurat)
})

read_h5ad <- function(path) {
  anndata_mod <- reticulate::import("anndata", convert = FALSE)
  scipy_sparse <- reticulate::import("scipy.sparse", convert = FALSE)
  ad <- anndata_mod$read_h5ad(path)
  obs_names <- reticulate::py_to_r(ad$obs_names$to_list())
  var_names <- reticulate::py_to_r(ad$var_names$to_list())
  source <- NULL
  if (reticulate::py_has_attr(ad$layers, "keys") && "counts" %in% as.character(reticulate::py_to_r(ad$layers$keys()))) {
    source <- ad$layers$get("counts")
  } else {
    source <- ad$X
  }
  if (reticulate::py_to_r(scipy_sparse$issparse(source))) {
    coo <- source$tocoo()
    counts <- Matrix::sparseMatrix(
      i = as.integer(reticulate::py_to_r(coo$col)) + 1L,
      j = as.integer(reticulate::py_to_r(coo$row)) + 1L,
      x = as.numeric(reticulate::py_to_r(coo$data)),
      dims = c(length(var_names), length(obs_names)),
      dimnames = list(var_names, obs_names)
    )
  } else {
    counts <- Matrix::Matrix(t(reticulate::py_to_r(source)), sparse = TRUE)
    colnames(counts) <- obs_names
    rownames(counts) <- var_names
  }
  Seurat::CreateSeuratObject(counts = counts)
}

write_h5ad <- function(input_path, path, embedding, n_pcs) {
  py <- reticulate::py_run_string("
def add_seurat_pca_and_write(input_path, output_path, embedding, n_pcs):
    import anndata
    import numpy as np

    ad = anndata.read_h5ad(input_path)
    ad.obsm['X_seurat_pca'] = np.asarray(embedding, dtype='float64')
    ad.uns['embedding'] = {
        'method': 'seurat_pca',
        'n_pcs': int(n_pcs),
        'obsm_key': 'X_seurat_pca',
    }
    ad.write_h5ad(output_path)
    check = anndata.read_h5ad(output_path)
    return list(check.obsm.keys())
")
  obsm_keys <- reticulate::py_to_r(py$add_seurat_pca_and_write(input_path, path, embedding, n_pcs))
  if (!("X_seurat_pca" %in% obsm_keys)) {
    stop(sprintf(
      "Seurat PCA wrote %s but obsm['X_seurat_pca'] is missing. Available obsm keys: %s",
      path,
      paste(obsm_keys, collapse = ", ")
    ))
  }
}

obj <- read_h5ad(input_h5ad)
if (ncol(obj) < 2 || nrow(obj) < 2) {
  stop("Seurat PCA requires at least 2 cells and 2 features.")
}
n_features <- min(n_features, nrow(obj))
n_pcs <- min(n_pcs, ncol(obj) - 1L, n_features - 1L)
if (n_pcs < 1) {
  stop("Seurat PCA could not select at least one valid principal component for this dataset.")
}
obj <- NormalizeData(obj, verbose = FALSE)
obj <- FindVariableFeatures(obj, nfeatures = n_features, verbose = FALSE)
obj <- ScaleData(obj, verbose = FALSE)
obj <- RunPCA(obj, npcs = n_pcs, verbose = FALSE, seed.use = seed)

embedding <- Seurat::Embeddings(obj, reduction = "pca")
if (is.null(embedding) || nrow(embedding) != ncol(obj) || ncol(embedding) == 0) {
  stop("Seurat PCA did not produce a valid cells x PCs embedding")
}
storage.mode(embedding) <- "double"
write_h5ad(input_h5ad, output_h5ad, embedding, n_pcs)

result <- list(
  status = "ok",
  output_h5ad = output_h5ad,
  method = "seurat_pca",
  embedding_key = "X_seurat_pca",
  n_pcs = n_pcs,
  n_cells = ncol(obj),
  n_features = nrow(obj)
)
cat(jsonlite::toJSON(result, auto_unbox = TRUE))
