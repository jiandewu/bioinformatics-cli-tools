# Utilities for reading and combining 10x Genomics Cell Ranger HDF5 matrices.

require_namespace <- function(package) {
  if (!requireNamespace(package, quietly = TRUE)) {
    stop("Package '", package, "' is required.", call. = FALSE)
  }
}

read_10x_h5 <- function(path, sample_id = NULL, feature_type = NULL,
                        unique_features = TRUE) {
  require_namespace("rhdf5")
  require_namespace("Matrix")

  if (!file.exists(path)) {
    stop("HDF5 file does not exist: ", path, call. = FALSE)
  }

  sample_id <- sample_id %||%
    tools::file_path_sans_ext(basename(path))

  read_dataset <- function(name) {
    rhdf5::h5read(path, paste0("matrix/", name))
  }

  counts <- Matrix::sparseMatrix(
    dims = as.integer(read_dataset("shape")),
    i = as.integer(read_dataset("indices")),
    p = as.integer(read_dataset("indptr")),
    x = as.numeric(read_dataset("data")),
    index1 = FALSE
  )

  feature_ids <- as.character(read_dataset("features/id"))
  feature_names <- tryCatch(
    as.character(read_dataset("features/name")),
    error = function(...) feature_ids
  )
  feature_types <- tryCatch(
    as.character(read_dataset("features/feature_type")),
    error = function(...) rep(NA_character_, length(feature_ids))
  )
  barcodes <- as.character(read_dataset("barcodes"))

  if (unique_features) {
    feature_names <- make.unique(feature_names)
  }

  rownames(counts) <- feature_names
  colnames(counts) <- paste(sample_id, barcodes, sep = "|")

  features <- data.frame(
    id = feature_ids,
    name = feature_names,
    feature_type = feature_types,
    stringsAsFactors = FALSE
  )

  if (!is.null(feature_type)) {
    keep <- !is.na(features$feature_type) &
      features$feature_type %in% feature_type
    counts <- counts[keep, , drop = FALSE]
    features <- features[keep, , drop = FALSE]
  }

  list(counts = counts, features = features, sample_id = sample_id)
}

merge_10x_h5 <- function(paths, sample_ids = NULL, feature_type = NULL,
                         unique_features = TRUE) {
  if (!length(paths)) {
    stop("No HDF5 files were supplied.", call. = FALSE)
  }

  paths <- normalizePath(paths, mustWork = TRUE)

  if (is.null(sample_ids)) {
    sample_ids <- tools::file_path_sans_ext(basename(paths))
  }
  if (length(sample_ids) != length(paths)) {
    stop("sample_ids must have the same length as paths.", call. = FALSE)
  }
  if (anyDuplicated(sample_ids)) {
    stop("sample_ids must be unique.", call. = FALSE)
  }

  matrices <- Map(
    function(path, sample_id) {
      read_10x_h5(
        path,
        sample_id = sample_id,
        feature_type = feature_type,
        unique_features = unique_features
      )
    },
    paths,
    sample_ids
  )

  reference_ids <- matrices[[1]]$features$id
  compatible <- vapply(
    matrices,
    function(item) identical(item$features$id, reference_ids),
    logical(1)
  )
  if (!all(compatible)) {
    stop(
      "Feature IDs and order differ across input files; merge is unsafe.",
      call. = FALSE
    )
  }

  counts <- do.call(cbind, lapply(matrices, `[[`, "counts"))
  features <- matrices[[1]]$features
  sparsity <- 1 - length(counts@x) /
    (as.double(nrow(counts)) * as.double(ncol(counts)))

  list(
    counts = counts,
    features = features,
    samples = data.frame(
      sample_id = sample_ids,
      path = paths,
      cells = vapply(matrices, function(item) ncol(item$counts), integer(1)),
      stringsAsFactors = FALSE
    ),
    summary = data.frame(
      genes = nrow(counts),
      cells = ncol(counts),
      sparsity = sparsity
    )
  )
}

`%||%` <- function(left, right) {
  if (is.null(left) || !length(left) || is.na(left) || !nzchar(left)) right else left
}
