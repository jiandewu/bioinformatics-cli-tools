#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1L) {
  stop("Usage: Rscript scripts/inspect_h5.R FILE.h5", call. = FALSE)
}

if (!requireNamespace("rhdf5", quietly = TRUE)) {
  stop("Package 'rhdf5' is required.", call. = FALSE)
}

path <- normalizePath(args[[1]], mustWork = TRUE)
cat("File:", path, "\n\n")
print(rhdf5::h5ls(path))
