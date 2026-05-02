#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(jsonlite)
  library(Matrix)
  library(MAST)
  library(S4Vectors)
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
input_h5ad <- params$input_h5ad
input_matrix <- params$input_matrix
input_obs <- params$input_obs
input_genes <- params$input_genes
input_cells <- params$input_cells
output_table <- params$output_table
group_key <- params$group_key
reference <- if (!is.null(params$reference)) params$reference else "rest"

read_exported_components <- function(matrix_path, obs_path, genes_path, cells_path) {
  counts <- Matrix::readMM(matrix_path)
  genes <- readLines(genes_path, warn = FALSE)
  cells <- readLines(cells_path, warn = FALSE)
  obs <- read.csv(obs_path, row.names = 1, check.names = FALSE, stringsAsFactors = FALSE)
  rownames(counts) <- genes
  colnames(counts) <- cells
  obs <- obs[cells, , drop = FALSE]
  list(counts = counts, obs = obs, genes = genes, cells = cells)
}

read_h5ad_components <- function(path) {
  if (requireNamespace("zellkonverter", quietly = TRUE)) {
    sce <- zellkonverter::readH5AD(path)
    assays <- SummarizedExperiment::assayNames(sce)
    assay_name <- if ("counts" %in% assays) "counts" else assays[[1]]
    counts <- SummarizedExperiment::assay(sce, assay_name)
    obs <- as.data.frame(SummarizedExperiment::colData(sce))
    genes <- rownames(sce)
    cells <- colnames(sce)
    return(list(counts = counts, obs = obs, genes = genes, cells = cells))
  }
  if (!requireNamespace("reticulate", quietly = TRUE)) {
    stop("MAST differential expression requires zellkonverter or reticulate to read .h5ad files.")
  }
  anndata <- reticulate::import("anndata", convert = FALSE)
  scipy_sparse <- reticulate::import("scipy.sparse", convert = FALSE)
  ad <- anndata$read_h5ad(path)
  source <- NULL
  if (reticulate::py_has_attr(ad$layers, "keys") && "counts" %in% reticulate::py_to_r(ad$layers$keys())) {
    source <- ad$layers$get("counts")
  } else {
    source <- ad$X
  }
  genes <- unlist(reticulate::py_to_r(ad$var_names$to_list()))
  cells <- unlist(reticulate::py_to_r(ad$obs_names$to_list()))
  if (reticulate::py_to_r(scipy_sparse$issparse(source))) {
    coo <- source$tocoo()
    counts <- Matrix::sparseMatrix(
      i = as.integer(reticulate::py_to_r(coo$col)) + 1L,
      j = as.integer(reticulate::py_to_r(coo$row)) + 1L,
      x = as.numeric(reticulate::py_to_r(coo$data)),
      dims = c(length(genes), length(cells))
    )
  } else {
    counts <- Matrix::Matrix(t(reticulate::py_to_r(source)), sparse = TRUE)
  }
  obs <- reticulate::py_to_r(ad$obs$copy())
  rownames(obs) <- cells
  rownames(counts) <- genes
  colnames(counts) <- cells
  list(counts = counts, obs = obs, genes = genes, cells = cells)
}

components <- if (!is.null(input_matrix)) {
  read_exported_components(input_matrix, input_obs, input_genes, input_cells)
} else {
  read_h5ad_components(input_h5ad)
}
counts <- components$counts
obs <- components$obs
genes <- components$genes
cells <- components$cells

if (!(group_key %in% colnames(obs))) {
  stop(sprintf("group_key '%s' not found in obs.", group_key))
}

group_values <- as.character(obs[[group_key]])
valid_groups <- sort(unique(group_values[!is.na(group_values)]))
if (!length(valid_groups)) {
  stop("No non-missing groups found for differential expression.")
}
if (!identical(reference, "rest") && !(reference %in% valid_groups)) {
  stop(sprintf("reference '%s' not found in obs[%s].", reference, group_key))
}

targets <- if (identical(reference, "rest")) valid_groups else setdiff(valid_groups, reference)
results <- list()
skipped <- list()

for (target in targets) {
  keep <- if (identical(reference, "rest")) {
    !is.na(group_values)
  } else {
    group_values %in% c(target, reference)
  }
  if (!any(keep)) {
    skipped[[target]] <- "no cells after filtering"
    next
  }

  condition <- ifelse(group_values[keep] == target, "target", "reference")
  n_target_cells <- sum(condition == "target")
  n_reference_cells <- sum(condition == "reference")
  if (n_target_cells < 3 || n_reference_cells < 3) {
    skipped[[target]] <- "fewer than 3 cells in target or reference"
    next
  }

  counts_sub <- counts[, keep, drop = FALSE]
  lib_size <- Matrix::colSums(counts_sub)
  lib_size[lib_size == 0] <- 1
  log_expr <- log1p(t(t(counts_sub) / lib_size * 1e6))
  well_ids <- colnames(counts_sub)
  if (is.null(well_ids)) {
    well_ids <- paste0("cell_", seq_len(ncol(counts_sub)))
  }

  cdata <- data.frame(
    wellKey = well_ids,
    condition = factor(condition, levels = c("reference", "target")),
    cngeneson = Matrix::colSums(counts_sub > 0),
    stringsAsFactors = FALSE,
    row.names = well_ids
  )
  fdata <- data.frame(
    primerid = genes,
    stringsAsFactors = FALSE,
    row.names = genes
  )
  sca <- MAST::FromMatrix(exprsArray = log_expr, cData = S4Vectors::DataFrame(cdata), fData = S4Vectors::DataFrame(fdata))
  fit <- MAST::zlm(~ condition + cngeneson, sca, silent = TRUE)
  summary_dt <- MAST::summary(fit, doLRT = "conditiontarget")$datatable

  hurdle <- summary_dt[summary_dt$contrast == "conditiontarget" & summary_dt$component == "H", c("primerid", "Pr(>Chisq)")]
  colnames(hurdle) <- c("gene", "pval")
  logfc <- summary_dt[summary_dt$contrast == "conditiontarget" & summary_dt$component == "logFC", c("primerid", "coef")]
  colnames(logfc) <- c("gene", "lfc")
  merged <- merge(hurdle, logfc, by = "gene", all = TRUE)
  if (!nrow(merged)) {
    skipped[[target]] <- "no test statistics returned by MAST"
    next
  }

  merged$pval_adj <- p.adjust(merged$pval, method = "BH")
  merged$group <- target
  merged$reference <- if (identical(reference, "rest")) "rest" else reference
  merged$method <- "mast"
  merged$n_target_cells <- n_target_cells
  merged$n_reference_cells <- n_reference_cells
  merged <- merged[order(merged$pval_adj, merged$pval, decreasing = FALSE, na.last = TRUE), , drop = FALSE]
  merged$rank <- seq_len(nrow(merged))
  results[[target]] <- merged[, c("group", "reference", "rank", "gene", "lfc", "pval", "pval_adj", "method", "n_target_cells", "n_reference_cells")]
}

if (length(results)) {
  out_df <- do.call(rbind, results)
} else {
  out_df <- data.frame(
    group = character(),
    reference = character(),
    rank = integer(),
    gene = character(),
    lfc = numeric(),
    pval = numeric(),
    pval_adj = numeric(),
    method = character(),
    n_target_cells = integer(),
    n_reference_cells = integer(),
    stringsAsFactors = FALSE
  )
}

write.csv(out_df, output_table, row.names = FALSE)

result <- list(
  status = "ok",
  method = "mast",
  group_key = group_key,
  output_table = output_table,
  n_groups = length(unique(out_df$group)),
  n_genes = length(genes),
  skipped_groups = skipped
)
cat(jsonlite::toJSON(result, auto_unbox = TRUE))
