# Volcano Plot CLI

Create publication-ready volcano plots from CSV or TSV differential-analysis
results. Column names, thresholds, title, dimensions, and output format are
configurable from the command line.

## Environment

```bash
conda env create -f environment.yml
conda activate volcano-plot-cli
```

## Usage

The input must contain a header. By default, the command reads `logFC` as the
log2 fold-change column and `adj.P.Val` as the significance column.

```bash
./volcano_plot.R \
  --input results.tsv \
  --output volcano.png \
  --fold-change-cutoff 2 \
  --significance-cutoff 0.001 \
  --title "Treatment vs control"
```

Use different column names when necessary:

```bash
./volcano_plot.R \
  --input results.csv \
  --output volcano.pdf \
  --fold-change-column log2FoldChange \
  --significance-column padj \
  --delimiter comma
```

Run `./volcano_plot.R --help` for all options. Rows with nonnumeric fold changes
or significance values outside `[0, 1]` are removed with a warning. A table with
no valid rows is rejected.

## Test

The smoke test generates a small synthetic table and verifies that a non-empty
PNG is produced:

```bash
./tests/smoke_test.sh
```

The repository contains code and synthetic test values only. Research data,
results, and manuscripts are excluded from version control.
