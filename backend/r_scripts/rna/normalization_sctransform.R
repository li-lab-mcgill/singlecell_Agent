#!/usr/bin/env Rscript

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
input_matrix <- params$input_matrix
input_genes <- params$input_genes
input_cells <- params$input_cells
output_matrix <- params$output_matrix
output_genes <- params$output_genes
output_cells <- params$output_cells

suppressPackageStartupMessages({
  library(Matrix)
  library(Seurat)
})

read_count_components <- function(matrix_path, genes_path, cells_path) {
  if (is.null(matrix_path) || is.null(genes_path) || is.null(cells_path)) {
    stop("SCTransform requires input_matrix, input_genes, and input_cells.")
  }
  counts <- Matrix::readMM(matrix_path)
  genes <- readLines(genes_path, warn = FALSE)
  cells <- readLines(cells_path, warn = FALSE)
  if (!identical(dim(counts), c(length(genes), length(cells)))) {
    stop(sprintf(
      "SCTransform input matrix shape %s does not match genes x cells (%d x %d).",
      paste(dim(counts), collapse = " x "),
      length(genes),
      length(cells)
    ))
  }
  rownames(counts) <- genes
  colnames(counts) <- cells
  Seurat::CreateSeuratObject(counts = counts)
}

write_matrix_outputs <- function(obj, matrix_path, genes_path, cells_path) {
  if (is.null(matrix_path) || is.null(genes_path) || is.null(cells_path)) {
    stop("SCTransform matrix output requires output_matrix, output_genes, and output_cells.")
  }
  data_mat <- tryCatch(
    Seurat::GetAssayData(obj[["SCT"]], layer = "data"),
    error = function(e) Seurat::GetAssayData(obj, assay = "SCT", slot = "data")
  )
  Matrix::writeMM(Matrix::t(data_mat), matrix_path)
  writeLines(rownames(data_mat), genes_path, useBytes = TRUE)
  writeLines(colnames(data_mat), cells_path, useBytes = TRUE)
}

obj <- read_count_components(input_matrix, input_genes, input_cells)
obj <- SCTransform(obj, verbose = FALSE, return.only.var.genes = FALSE)
write_matrix_outputs(obj, output_matrix, output_genes, output_cells)

result <- list(
  status = "ok",
  output_matrix = output_matrix,
  method = "sctransform",
  n_cells = ncol(obj),
  n_features = nrow(obj)
)
cat(jsonlite::toJSON(result, auto_unbox = TRUE))
