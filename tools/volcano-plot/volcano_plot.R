#!/usr/bin/env Rscript

usage <- function() {
  cat(paste0(
    "Usage:\n",
    "  volcano_plot.R --input TABLE --output FIGURE [options]\n\n",
    "Required:\n",
    "  --input PATH                  CSV or TSV table with a header\n",
    "  --output PATH                 Output image supported by ggplot2\n\n",
    "Options:\n",
    "  --fold-change-column NAME     Fold-change column [logFC]\n",
    "  --significance-column NAME    P/q-value column [adj.P.Val]\n",
    "  --fold-change-cutoff NUMBER   Absolute log2 fold-change cutoff [2]\n",
    "  --significance-cutoff NUMBER  Significance cutoff [0.001]\n",
    "  --delimiter VALUE             auto, tab, or comma [auto]\n",
    "  --title TEXT                  Plot title [none]\n",
    "  --width NUMBER                Figure width in inches [7]\n",
    "  --height NUMBER               Figure height in inches [6]\n",
    "  --dpi INTEGER                 Raster resolution [300]\n",
    "  -h, --help                    Show this help\n"
  ))
}

abort <- function(message) {
  stop(message, call. = FALSE)
}

parse_cli <- function(args) {
  options <- list(
    input = NULL,
    output = NULL,
    fold_change_column = "logFC",
    significance_column = "adj.P.Val",
    fold_change_cutoff = 2,
    significance_cutoff = 0.001,
    delimiter = "auto",
    title = "",
    width = 7,
    height = 6,
    dpi = 300
  )
  keys <- c(
    "--input" = "input",
    "--output" = "output",
    "--fold-change-column" = "fold_change_column",
    "--significance-column" = "significance_column",
    "--fold-change-cutoff" = "fold_change_cutoff",
    "--significance-cutoff" = "significance_cutoff",
    "--delimiter" = "delimiter",
    "--title" = "title",
    "--width" = "width",
    "--height" = "height",
    "--dpi" = "dpi"
  )

  if (length(args) == 0 || any(args %in% c("-h", "--help"))) {
    usage()
    quit(status = 0)
  }

  index <- 1
  while (index <= length(args)) {
    option <- args[[index]]
    if (!option %in% names(keys)) {
      abort(paste("unknown option:", option))
    }
    if (index == length(args)) {
      abort(paste("missing value for", option))
    }
    options[[keys[[option]]]] <- args[[index + 1]]
    index <- index + 2
  }

  if (is.null(options$input) || is.null(options$output)) {
    abort("--input and --output are required")
  }

  numeric_options <- c(
    "fold_change_cutoff", "significance_cutoff", "width", "height", "dpi"
  )
  for (name in numeric_options) {
    value <- suppressWarnings(as.numeric(options[[name]]))
    if (!is.finite(value)) {
      abort(paste("invalid numeric value for", gsub("_", "-", name)))
    }
    options[[name]] <- value
  }

  if (options$fold_change_cutoff < 0) {
    abort("fold-change-cutoff must be non-negative")
  }
  if (options$significance_cutoff <= 0 || options$significance_cutoff > 1) {
    abort("significance-cutoff must be greater than 0 and at most 1")
  }
  if (options$width <= 0 || options$height <= 0 || options$dpi <= 0) {
    abort("width, height, and dpi must be positive")
  }
  if (!options$delimiter %in% c("auto", "tab", "comma")) {
    abort("delimiter must be auto, tab, or comma")
  }

  options
}

read_input <- function(path, delimiter) {
  if (!file.exists(path)) {
    abort(paste("input file does not exist:", path))
  }
  if (delimiter == "auto") {
    delimiter <- if (grepl("\\.csv$", path, ignore.case = TRUE)) "comma" else "tab"
  }
  separator <- if (delimiter == "comma") "," else "\t"
  read.table(
    path,
    header = TRUE,
    sep = separator,
    quote = "\"",
    comment.char = "",
    check.names = FALSE,
    stringsAsFactors = FALSE
  )
}

main <- function() {
  args <- parse_cli(commandArgs(trailingOnly = TRUE))
  if (!requireNamespace("ggplot2", quietly = TRUE)) {
    abort("package 'ggplot2' is required; create the included Conda environment")
  }

  data <- read_input(args$input, args$delimiter)
  required <- c(args$fold_change_column, args$significance_column)
  missing <- setdiff(required, names(data))
  if (length(missing) > 0) {
    abort(paste("missing columns:", paste(missing, collapse = ", ")))
  }

  fold_change <- suppressWarnings(as.numeric(data[[args$fold_change_column]]))
  significance <- suppressWarnings(as.numeric(data[[args$significance_column]]))
  valid <- is.finite(fold_change) & is.finite(significance) &
    significance >= 0 & significance <= 1
  if (!any(valid)) {
    abort("no valid rows remain after numeric and significance-range checks")
  }
  if (any(!valid)) {
    warning(sum(!valid), " invalid row(s) removed", call. = FALSE)
  }

  plot_data <- data.frame(
    fold_change = fold_change[valid],
    significance = significance[valid]
  )
  is_significant <- plot_data$significance <= args$significance_cutoff &
    abs(plot_data$fold_change) >= args$fold_change_cutoff
  plot_data$group <- ifelse(
    is_significant,
    ifelse(plot_data$fold_change > 0, "Up", "Down"),
    "Not significant"
  )
  plot_data$group <- factor(
    plot_data$group,
    levels = c("Up", "Down", "Not significant")
  )
  plot_data$negative_log10 <- -log10(
    pmax(plot_data$significance, .Machine$double.xmin)
  )

  palette <- c(
    "Up" = "#D55E00",
    "Down" = "#0072B2",
    "Not significant" = "#B3B3B3"
  )
  plot <- ggplot2::ggplot(
    plot_data,
    ggplot2::aes(x = fold_change, y = negative_log10, color = group)
  ) +
    ggplot2::geom_point(alpha = 0.8, size = 1.2) +
    ggplot2::geom_hline(
      yintercept = -log10(args$significance_cutoff),
      linetype = "dashed",
      linewidth = 0.4
    ) +
    ggplot2::geom_vline(
      xintercept = c(-args$fold_change_cutoff, args$fold_change_cutoff),
      linetype = "dashed",
      linewidth = 0.4
    ) +
    ggplot2::scale_color_manual(values = palette, drop = FALSE) +
    ggplot2::labs(
      x = "log2 fold change",
      y = "-log10 significance",
      color = NULL,
      title = args$title
    ) +
    ggplot2::theme_bw(base_size = 12) +
    ggplot2::theme(
      panel.grid = ggplot2::element_blank(),
      plot.title = ggplot2::element_text(hjust = 0.5, face = "bold")
    )

  output_directory <- dirname(args$output)
  if (!dir.exists(output_directory)) {
    abort(paste("output directory does not exist:", output_directory))
  }
  ggplot2::ggsave(
    filename = args$output,
    plot = plot,
    width = args$width,
    height = args$height,
    dpi = args$dpi,
    bg = "white"
  )
}

tryCatch(
  main(),
  error = function(error) {
    message("error: ", conditionMessage(error))
    quit(status = 2)
  }
)
