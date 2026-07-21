#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2L) {
  stop(
    "Usage: Rscript scripts/merge_h5.R OUTPUT.rds INPUT1.h5 [INPUT2.h5 ...]",
    call. = FALSE
  )
}

script_arg <- grep("^--file=", commandArgs(), value = TRUE)
script_path <- sub("^--file=", "", script_arg[[1]])
source(file.path(dirname(dirname(normalizePath(script_path))), "R", "cellranger_h5.R"))

output_path <- args[[1]]
input_paths <- args[-1]
result <- merge_10x_h5(input_paths)

saveRDS(result, output_path)
cat(
  "Saved", result$summary$cells, "cells and",
  result$summary$genes, "features to", output_path, "\n"
)
