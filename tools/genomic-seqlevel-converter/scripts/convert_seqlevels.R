#!/usr/bin/env Rscript

usage <- function() {
  cat(
    "Usage:\n",
    "  Rscript scripts/convert_seqlevels.R INPUT OUTPUT STYLE\n\n",
    "Arguments:\n",
    "  INPUT   Input GFF, GFF3, GTF, BED, or another rtracklayer format\n",
    "  OUTPUT  New output file; an existing file will not be overwritten\n",
    "  STYLE   Target sequence-name style, such as UCSC, Ensembl, or NCBI\n",
    sep = ""
  )
}

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 3L) {
  usage()
  quit(status = 2L)
}

input_path <- args[[1]]
output_path <- args[[2]]
target_style <- args[[3]]

for (package in c("GenomeInfoDb", "rtracklayer")) {
  if (!requireNamespace(package, quietly = TRUE)) {
    stop("Package '", package, "' is required.", call. = FALSE)
  }
}

if (!file.exists(input_path)) {
  stop("Input file does not exist: ", input_path, call. = FALSE)
}
if (file.exists(output_path)) {
  stop("Refusing to overwrite existing output: ", output_path, call. = FALSE)
}

input_path <- normalizePath(input_path, mustWork = TRUE)
output_dir <- dirname(output_path)
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
output_dir <- normalizePath(output_dir, mustWork = TRUE)
output_path <- file.path(output_dir, basename(output_path))

annotation <- rtracklayer::import(input_path)
style_before <- GenomeInfoDb::seqlevelsStyle(annotation)

GenomeInfoDb::seqlevelsStyle(annotation) <- target_style
style_after <- GenomeInfoDb::seqlevelsStyle(annotation)

rtracklayer::export(annotation, output_path)

cat(
  "Converted", length(annotation), "annotation records.\n",
  "Input style:", paste(style_before, collapse = ", "), "\n",
  "Output style:", paste(style_after, collapse = ", "), "\n",
  "Output:", output_path, "\n"
)
