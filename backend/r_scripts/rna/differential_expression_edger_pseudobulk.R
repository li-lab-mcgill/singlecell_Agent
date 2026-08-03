#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(jsonlite)
  library(Matrix)
  library(edgeR)
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
sample_key <- params$sample_key

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
    stop("edgeR pseudobulk requires zellkonverter or reticulate to read .h5ad files.")
  }
  anndata <- reticulate::import("anndata", convert = FALSE)
  scipy_sparse <- reticulate::import("scipy.sparse", convert = FALSE)
  ad <- anndata$read_h5ad(path)
  source <- NULL
  if (reticulate::py_has_attr(ad$layers, "keys") && "counts" %in% as.character(reticulate::py_to_r(ad$layers$keys()))) {
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

build_pseudobulk <- function(counts, groups, samples, target, reference) {
  keep <- !is.na(groups) & !is.na(samples)
  groups <- groups[keep]
  samples <- samples[keep]
  counts <- counts[, keep, drop = FALSE]

  if (identical(reference, "rest")) {
    condition <- ifelse(groups == target, "target", "reference")
  } else {
    subset_keep <- groups %in% c(target, reference)
    groups <- groups[subset_keep]
    samples <- samples[subset_keep]
    counts <- counts[, subset_keep, drop = FALSE]
    condition <- ifelse(groups == target, "target", "reference")
  }

  cols <- list()
  meta <- list()
  seen <- 0L
  for (sample_id in unique(samples)) {
    sample_mask <- samples == sample_id
    for (condition_name in c("target", "reference")) {
      mask <- sample_mask & condition == condition_name
      if (!any(mask)) {
        next
      }
      seen <- seen + 1L
      cols[[seen]] <- Matrix::rowSums(counts[, mask, drop = FALSE])
      meta[[seen]] <- data.frame(
        pseudobulk_id = paste(sample_id, condition_name, sep = "__"),
        sample_id = sample_id,
        condition = condition_name,
        stringsAsFactors = FALSE
      )
    }
  }
  if (!length(cols)) {
    return(NULL)
  }
  pb_counts <- do.call(cbind, cols)
  pb_meta <- do.call(rbind, meta)
  colnames(pb_counts) <- pb_meta$pseudobulk_id
  rownames(pb_counts) <- rownames(counts)
  rownames(pb_meta) <- pb_meta$pseudobulk_id
  list(counts = pb_counts, meta = pb_meta)
}

components <- if (!is.null(input_matrix)) {
  read_exported_components(input_matrix, input_obs, input_genes, input_cells)
} else {
  read_h5ad_components(input_h5ad)
}
counts <- components$counts
obs <- components$obs
genes <- components$genes

if (!(group_key %in% colnames(obs))) {
  stop(sprintf("group_key '%s' not found in obs.", group_key))
}
if (!(sample_key %in% colnames(obs))) {
  stop(sprintf("sample_key '%s' not found in obs.", sample_key))
}

group_values <- as.character(obs[[group_key]])
sample_values <- as.character(obs[[sample_key]])
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
  pb <- build_pseudobulk(counts, group_values, sample_values, target, reference)
  if (is.null(pb)) {
    skipped[[target]] <- "no pseudobulk columns could be constructed"
    next
  }

  meta <- pb$meta
  pb_counts <- pb$counts
  condition_counts <- table(meta$condition)
  if (!all(c("target", "reference") %in% names(condition_counts)) || any(condition_counts[c("target", "reference")] < 2)) {
    skipped[[target]] <- "need at least 2 pseudobulk samples in both target and reference conditions"
    next
  }

  sample_table <- table(meta$sample_id)
  paired_samples <- names(sample_table[sample_table == 2])
  use_paired <- length(paired_samples) >= 2
  if (use_paired) {
    keep_cols <- rownames(meta) %in% unlist(lapply(paired_samples, function(sample_id) {
      rownames(meta)[meta$sample_id == sample_id]
    }))
    meta <- meta[keep_cols, , drop = FALSE]
    pb_counts <- pb_counts[, rownames(meta), drop = FALSE]
  }

  meta$condition <- factor(meta$condition, levels = c("reference", "target"))
  design <- if (use_paired) {
    meta$sample_id <- factor(meta$sample_id)
    model.matrix(~ sample_id + condition, data = meta)
  } else {
    model.matrix(~ condition, data = meta)
  }

  y <- edgeR::DGEList(pb_counts)
  keep_genes <- edgeR::filterByExpr(y, design)
  if (!any(keep_genes)) {
    skipped[[target]] <- "all genes filtered by edgeR::filterByExpr"
    next
  }
  y <- y[keep_genes, , keep.lib.sizes = FALSE]
  y <- edgeR::calcNormFactors(y)
  y <- edgeR::estimateDisp(y, design)
  fit <- edgeR::glmQLFit(y, design, robust = TRUE)
  test <- edgeR::glmQLFTest(fit, coef = "conditiontarget")
  tt <- edgeR::topTags(test, n = Inf, sort.by = "PValue")$table
  tt$gene <- rownames(tt)
  cpm_means <- rowMeans(edgeR::cpm(y, log = FALSE))
  tt$base_mean <- cpm_means[rownames(tt)]
  tt$group <- target
  tt$reference <- if (identical(reference, "rest")) "rest" else reference
  tt$method <- "edger_pseudobulk"
  tt$n_target_samples <- sum(meta$condition == "target")
  tt$n_reference_samples <- sum(meta$condition == "reference")
  tt$paired_design <- use_paired
  tt$rank <- seq_len(nrow(tt))
  names(tt)[names(tt) == "PValue"] <- "pval"
  names(tt)[names(tt) == "FDR"] <- "pval_adj"
  names(tt)[names(tt) == "F"] <- "statistic"
  results[[target]] <- tt[, c("group", "reference", "rank", "gene", "logFC", "pval", "pval_adj", "statistic", "base_mean", "method", "n_target_samples", "n_reference_samples", "paired_design")]
  names(results[[target]])[names(results[[target]]) == "logFC"] <- "lfc"
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
    statistic = numeric(),
    base_mean = numeric(),
    method = character(),
    n_target_samples = integer(),
    n_reference_samples = integer(),
    paired_design = logical(),
    stringsAsFactors = FALSE
  )
}

write.csv(out_df, output_table, row.names = FALSE)

result <- list(
  status = "ok",
  method = "edger_pseudobulk",
  group_key = group_key,
  sample_key = sample_key,
  output_table = output_table,
  n_groups = length(unique(out_df$group)),
  n_genes = length(genes),
  skipped_groups = skipped
)
cat(jsonlite::toJSON(result, auto_unbox = TRUE))
