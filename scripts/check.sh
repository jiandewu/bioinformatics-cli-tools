#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python_bin=${PYTHON:-python3}
rscript_bin=${RSCRIPT:-Rscript}

cd "$project_dir"

(
  cd tools/fastqc-summary
  PYTHONDONTWRITEBYTECODE=1 "$python_bin" -m unittest discover -s tests -v
)
(
  cd tools/tabular-column-selector
  PYTHONDONTWRITEBYTECODE=1 "$python_bin" -m unittest discover -s tests -v
)
(
  cd tools/delimited-table-transformer
  PYTHONDONTWRITEBYTECODE=1 "$python_bin" -m unittest discover -s tests -v
)

if command -v "$rscript_bin" >/dev/null 2>&1 || test -x "$rscript_bin"; then
  R_DEFAULT_PACKAGES=NULL "$rscript_bin" --vanilla -e '
    files <- c(
      "tools/volcano-plot/volcano_plot.R",
      "tools/genomic-seqlevel-converter/scripts/convert_seqlevels.R",
      "tools/cellranger-hdf5-utils/R/cellranger_h5.R",
      "tools/cellranger-hdf5-utils/scripts/inspect_h5.R",
      "tools/cellranger-hdf5-utils/scripts/merge_h5.R"
    )
    invisible(lapply(files, parse))
    cat("R syntax checks passed.\n")
  '
else
  printf 'R syntax checks skipped: Rscript not found.\n' >&2
fi

sh -n tools/volcano-plot/tests/smoke_test.sh
printf 'Python tests and available syntax checks passed.\n'
