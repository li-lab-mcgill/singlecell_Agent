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
  library(SingleCellExperiment)
  library(scran)
  library(scater)
})

read_count_components_as_sce <- function(matrix_path, genes_path, cells_path) {
  if (is.null(matrix_path) || is.null(genes_path) || is.null(cells_path)) {
    stop("scran normalization requires input_matrix, input_genes, and input_cells.")
  }
  counts <- Matrix::readMM(matrix_path)
  genes <- readLines(genes_path, warn = FALSE)
  cells <- readLines(cells_path, warn = FALSE)
  if (!identical(dim(counts), c(length(genes), length(cells)))) {
    stop(sprintf(
      "scran input matrix shape %s does not match genes x cells (%d x %d).",
      paste(dim(counts), collapse = " x "),
      length(genes),
      length(cells)
    ))
  }
  rownames(counts) <- genes
  colnames(counts) <- cells
  SingleCellExperiment::SingleCellExperiment(assays = list(counts = counts))
}

write_matrix_outputs <- function(sce, matrix_path, genes_path, cells_path) {
  if (is.null(matrix_path) || is.null(genes_path) || is.null(cells_path)) {
    stop("scran matrix output requires output_matrix, output_genes, and output_cells.")
  }
  mat <- SingleCellExperiment::logcounts(sce)
  Matrix::writeMM(Matrix::t(mat), matrix_path)
  writeLines(rownames(sce), genes_path, useBytes = TRUE)
  writeLines(colnames(sce), cells_path, useBytes = TRUE)
}

sce <- read_count_components_as_sce(input_matrix, input_genes, input_cells)
clusters <- NULL
if (ncol(sce) >= 20) {
  clusters <- tryCatch(scran::quickCluster(sce), error = function(e) NULL)
}
sce <- if (is.null(clusters)) {
  scran::computeSumFactors(sce)
} else {
  scran::computeSumFactors(sce, clusters = clusters)
}
sce <- scater::logNormCounts(sce)
write_matrix_outputs(sce, output_matrix, output_genes, output_cells)

result <- list(
  status = "ok",
  output_matrix = output_matrix,
  method = "scran",
  n_cells = ncol(sce),
  n_features = nrow(sce)
)
cat(jsonlite::toJSON(result, auto_unbox = TRUE))
